# PowerShell script to test Gemma RAG Service with curl
# Sends front, left, and right posture views separately

# Configuration
$GEMMA_RAG_URL = if ($env:GEMMA_RAG_URL) { $env:GEMMA_RAG_URL } else { "http://localhost:8000/v1/rag/query" }
$SCRIPT_DIR = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $SCRIPT_DIR

Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Gemma RAG Multimodal Test (PowerShell)" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Endpoint: $GEMMA_RAG_URL"
Write-Host ""

# Function to encode image to base64
function Encode-ImageToBase64 {
    param([string]$ImagePath)
    
    $bytes = [System.IO.File]::ReadAllBytes($ImagePath)
    return [Convert]::ToBase64String($bytes)
}

# Function to extract metrics for a specific view
function Get-ViewMetrics {
    param([string]$View)
    
    $json = Get-Content "test.txt" -Raw | ConvertFrom-Json
    $metrics = $json.metrics_by_view.$View
    
    if ($metrics) {
        return ($metrics | ConvertTo-Json -Depth 10 -Compress)
    } else {
        return "{}"
    }
}

# Function to send a single query
function Send-PostureQuery {
    param(
        [string]$View,
        [string]$ImageFile,
        [string]$Query
    )
    
    Write-Host ""
    Write-Host "==========================================  " -ForegroundColor Blue
    Write-Host "Testing $View view" -ForegroundColor Blue
    Write-Host "==========================================" -ForegroundColor Blue
    Write-Host "Query: $Query"
    Write-Host "Image: $ImageFile"
    
    # Check if image exists
    if (-not (Test-Path $ImageFile)) {
        Write-Host "[ERROR] Image not found: $ImageFile" -ForegroundColor Red
        return $false
    }
    
    # Encode image
    Write-Host "Encoding image to base64..."
    try {
        $imageBase64 = Encode-ImageToBase64 -ImagePath $ImageFile
        $imageSize = $imageBase64.Length
        Write-Host "[OK] Image encoded: $imageSize bytes"
    } catch {
        Write-Host "[ERROR] Failed to encode image: $_" -ForegroundColor Red
        return $false
    }
    
    # Extract metrics
    Write-Host "Extracting metrics for $View view..."
    $metrics = Get-ViewMetrics -View $View
    
    if ($metrics -eq "{}") {
        Write-Host "[WARN] No metrics found for $View view" -ForegroundColor Yellow
    } else {
        Write-Host "[OK] Metrics extracted"
    }
    
    # Build JSON payload
    Write-Host "Building request payload..."
    
    # Escape quotes in query
    $queryEscaped = $Query -replace '"', '\"'
    
    $payload = @"
{
  "query": "$queryEscaped",
  "history": [],
  "translate": true,
  "top_k": 5,
  "metrics": $metrics,
  "image_base64": "$imageBase64"
}
"@
    
    # Save payload to temp file
    $tempFile = [System.IO.Path]::GetTempFileName()
    $payload | Out-File -FilePath $tempFile -Encoding UTF8 -NoNewline
    
    # Send request
    Write-Host ""
    Write-Host "Sending request to Gemma RAG service..."
    $startTime = Get-Date
    Write-Host "Started at: $($startTime.ToString('HH:mm:ss'))"
    
    try {
        $response = curl.exe -s -X POST $GEMMA_RAG_URL `
            -H "Content-Type: application/json" `
            --data-binary "@$tempFile" `
            --max-time 90 `
            -w "`nHTTP_STATUS:%{http_code}"
        
        $endTime = Get-Date
        $elapsed = ($endTime - $startTime).TotalSeconds
        
        # Clean up temp file
        Remove-Item $tempFile -ErrorAction SilentlyContinue
        
        # Parse response
        $lines = $response -split "`n"
        $statusLine = $lines | Where-Object { $_ -match "HTTP_STATUS:" }
        $httpStatus = if ($statusLine) { ($statusLine -split ":")[1] } else { "000" }
        $responseBody = ($lines | Where-Object { $_ -notmatch "HTTP_STATUS:" }) -join "`n"
        
        Write-Host "Completed in: $([math]::Round($elapsed, 2))s"
        Write-Host ""
        
        if ($httpStatus -eq "200") {
            Write-Host "[SUCCESS] HTTP $httpStatus" -ForegroundColor Green
            Write-Host ""
            Write-Host "------------------------------------------------------------"
            Write-Host "RAG Response:"
            Write-Host "------------------------------------------------------------"
            
            # Parse and display response
            try {
                $jsonResponse = $responseBody | ConvertFrom-Json
                Write-Host $jsonResponse.content
                Write-Host ""
                
                $contextLen = if ($jsonResponse.retrieved_context) { $jsonResponse.retrieved_context.Length } else { 0 }
                $sourcesCount = if ($jsonResponse.sources) { $jsonResponse.sources.Count } else { 0 }
                
                Write-Host "Context length: $contextLen chars"
                Write-Host "Sources: $sourcesCount documents"
            } catch {
                Write-Host $responseBody
            }
            
            Write-Host "------------------------------------------------------------"
            
            # Save response to file
            $outputFile = "${View}_response.json"
            $responseBody | Out-File -FilePath $outputFile -Encoding UTF8
            Write-Host ""
            Write-Host "Full response saved to: $outputFile"
            
            return $true
        } else {
            Write-Host "[ERROR] HTTP $httpStatus" -ForegroundColor Red
            Write-Host ""
            Write-Host "Error response:"
            Write-Host $responseBody
            return $false
        }
        
    } catch {
        Write-Host "[ERROR] Request failed: $_" -ForegroundColor Red
        return $false
    } finally {
        # Clean up temp file
        if (Test-Path $tempFile) {
            Remove-Item $tempFile -ErrorAction SilentlyContinue
        }
    }
}

# Main execution
Write-Host "Checking dependencies..."

# Check for curl
if (-not (Get-Command curl.exe -ErrorAction SilentlyContinue)) {
    Write-Host "[ERROR] curl not found. Please install curl." -ForegroundColor Red
    exit 1
}
Write-Host "  [OK] curl"

# Check required files
Write-Host ""
Write-Host "Checking required files..."

if (-not (Test-Path "test.txt")) {
    Write-Host "[ERROR] test.txt not found" -ForegroundColor Red
    exit 1
}
Write-Host "  [OK] test.txt"

$images = @{
    "front" = "front_b27a3c9f_clinical.png"
    "left"  = "left_a1b6ab98_clinical.png"
    "right" = "right_3a65a04f_clinical.png"
}

foreach ($view in $images.Keys) {
    if (Test-Path $images[$view]) {
        Write-Host "  [OK] $($images[$view])"
    } else {
        Write-Host "  [ERROR] $($images[$view]) not found" -ForegroundColor Red
        exit 1
    }
}

# Test queries
$queries = @{
    "front" = "Please analyze my frontal posture based on these measurements. What do you notice?"
    "left"  = "Please analyze my left side posture. What can you tell me about my alignment?"
    "right" = "Please analyze my right side posture. Are there any concerns?"
}

# Run tests
$successCount = 0
$failCount = 0

foreach ($view in @("front", "left", "right")) {
    if (Send-PostureQuery -View $view -ImageFile $images[$view] -Query $queries[$view]) {
        $successCount++
    } else {
        $failCount++
    }
    
    # Wait between requests (except after last one)
    if ($view -ne "right") {
        Write-Host ""
        Write-Host "Waiting 2 seconds before next request..." -ForegroundColor Yellow
        Start-Sleep -Seconds 2
    }
}

# Summary
Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "TEST SUMMARY" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Successful: $successCount/3" -ForegroundColor Green

if ($failCount -gt 0) {
    Write-Host "Failed: $failCount/3" -ForegroundColor Red
}

Write-Host ""
Write-Host "Response files:"
foreach ($view in @("front", "left", "right")) {
    $responseFile = "${view}_response.json"
    if (Test-Path $responseFile) {
        Write-Host "  - $responseFile"
    }
}

Write-Host ""
Write-Host "Done!" -ForegroundColor Green
