1 – Research and understand before changing
Before changing any code, invest time in understanding how the current system works and why it is built the way it is. Top developers avoid leaping straight into implementation. They:

Explore the code base at a high level. Sketch out the architecture, look for top‑level classes or modules and identify how data flows. When joining a new project or exploring unfamiliar code, start from the user interface or API and drill down
amberwilson.co.uk
. It is not necessary to understand the entire code base, but you should understand the part you intend to modify and its dependencies
amberwilson.co.uk
.

Run the program locally and use it like an end user. This reveals how components interact and surfaces any unexpected behaviour
amberwilson.co.uk
.

Read documentation and ask questions. Seek internal docs or ask colleagues for context when you cannot quickly find answers
amberwilson.co.uk
.

Use debugging and tests to verify assumptions. Step through the code with a debugger, run existing unit/integration tests and examine logs. This establishes a baseline and helps confirm what the code does
medium.com
.

Approach the codebase with healthy scepticism. Do not assume best practices were followed. Understand what works well and what doesn’t
medium.com
.

2 – Plan changes based on evidence, not impulse
Once you understand the problem and the code around it, plan your solution before writing any code.

Confirm the bug or requirement. Reproduce the issue, collect evidence, and ensure it is not already fixed upstream or by another contributor. For example, before working on a fix, the Ubuntu packaging guide recommends checking upstream bug trackers and revision history
canonical-ubuntu-packaging-guide.readthedocs-hosted.com
.

Scope the change. Decide whether a minimal fix will suffice or whether a larger refactor is justified. The Software Engineering community notes that rewriting code without understanding the bug is risky
softwareengineering.stackexchange.com
. The default strategy should be to repair existing code rather than rewrite it
softwareengineering.stackexchange.com
, especially when tests are limited
softwareengineering.stackexchange.com
.

Assess test coverage. Determine whether there are unit or integration tests covering the affected area. If tests exist, run them and ensure they pass before modification
medium.com
. If no tests exist, write a test that reproduces the bug or demonstrates the required behaviour. This failing test becomes the guide for your fix
softwareengineering.stackexchange.com
.

Decide whether to involve project management or peers. For complex bugs or refactors close to a release date, consult your project manager. Major changes may have business implications and should not be made unilaterally
softwareengineering.stackexchange.com
.

3 – Follow the “least‑resistance” bug‑fixing strategy
Claude should prefer minimal, low‑risk fixes over large rewrites. This path of least resistance reduces the chance of introducing new bugs and makes code reviews easier.

Create a small, failing test (“red”) that exposes the bug, then write just enough code to make the test pass (“green”), and finally refactor for clarity if needed (“refactor”). This “Red–Green–Refactor” cycle from test‑driven development ensures that you only change what is necessary and that the fix is verified by tests
softwareengineering.stackexchange.com
.

Keep changes minimal. The Ubuntu packaging guide explicitly advises keeping changes as minimal as possible and documenting your assumptions
canonical-ubuntu-packaging-guide.readthedocs-hosted.com
. Avoid modifying unrelated parts of the code base. If you need to improve surrounding code to make the fix easier, split those improvements into separate, well‑tested commits or tasks
medium.com
.

Resist the temptation to rewrite. Even if you see poorly written code, remember it is running in production and providing value. Treat existing code as fragile and make small, incremental changes instead of wholesale rewrites
medium.com
. Follow the Open/Closed principle: extend behaviour via new functions or classes rather than modifying existing ones
medium.com
.

Use simple solutions (KISS). Favor straightforward, readable fixes over clever but complex approaches. The Medium article notes that keeping changes simple makes them easier to review and less likely to introduce errors
medium.com
.

Document assumptions and decisions. Explain why you chose a particular approach, especially if you decided against a larger refactor. This helps future maintainers understand the context.
canonical-ubuntu-packaging-guide.readthedocs-hosted.com

4 – Write clean, modular and testable code
When implementing your fix or new feature, follow standard coding conventions to make the code easy to understand and maintain:

Keep functions short and focused. Each function should perform one task
zencoder.ai
. Break complex logic into smaller functions or methods.

Use descriptive names for variables, functions and classes to convey intent
zencoder.ai
.

Avoid duplication. Extract common logic into shared functions so that changes need to be made in only one place
zencoder.ai
.

Write automated tests for your new or modified code
zencoder.ai
. Tests serve as a safety net against regressions.

Follow a consistent coding style. Use the repository’s linting and formatting tools to keep the style uniform
zencoder.ai
.

5 – Preserve existing functionality and avoid removing code
Claude should never remove or delete working code unless explicitly instructed and justified. When deprecating functionality or changing behaviour, follow these practices:

Leave existing APIs intact and add new interfaces. This honours the Open/Closed principle
medium.com
 and reduces the risk of breaking dependent components.

Mark outdated functions as deprecated rather than deleting them. Use language‑specific mechanisms (e.g., @deprecated annotations or comments) to signal that a method should no longer be used, but keep it until a major release so existing clients continue to work.

Maintain backward compatibility in data structures and interfaces. When changing file formats or APIs, provide migration paths or compatibility layers.

Only remove code after confirming it is unused and when project maintainers agree. Large removals should be discussed in an issue or pull request with justification.

6 – Prepare high‑quality patches
When submitting your changes for review, respect the maintainers’ time and make your patch easy to evaluate:

Send a minimal diff, not whole files. The Linux Documentation Project notes that it is the contributor’s responsibility to track the current code and submit a minimal patch against the latest version
tldp.org
. Avoid including changes to generated files or unrelated whitespace changes
tldp.org
.

Document user‑visible changes. Include updates to documentation, man pages, or comments as part of your patch
tldp.org
. Good documentation shows that you understand the impact of your change.

Provide an explanation with your patch. Cover notes should describe why the change is needed, how it was implemented and any trade‑offs
tldp.org
. Be honest about risks or limitations.

Follow the project’s contribution guidelines. Adhere to commit message conventions, code review processes and branch policies.

7 – Seek feedback and iterate
After submitting your fix, incorporate feedback from reviewers. Use code reviews as an opportunity to learn and improve. If reviewers request changes, update your patch and ensure all tests continue to pass. Encourage pair programming or collaborative review sessions when appropriate
amberwilson.co.uk
.

8 – Balance bug fixes with code health
It is tempting to clean up messy code while fixing bugs. While following the Boy‑Scout principle of leaving the code cleaner than you found it is laudable, you must balance it against the risk of breaking working functionality. Rewriting code can introduce new bugs and affect other parts of the system
softwareengineering.stackexchange.com
. Use judgement:

Improve code where tests provide sufficient safety. If strong regression tests exist around the area you are changing, small refactors to improve clarity or design are acceptable.

Create separate tickets for larger refactors. Don’t fold major redesigns into bug‑fix commits. Track technical debt and schedule dedicated time to address it
softwareengineering.stackexchange.com
.

9 – Continuous integration and code review
Your changes should integrate smoothly into the development workflow:

Automate tests and builds. Configure the CI pipeline to run unit, integration and end‑to‑end tests for every change. Only merge code that passes all checks
zencoder.ai
.

Conduct thorough code reviews. Encourage reviewers to restate what the code does, verify edge cases and ensure that temporary workarounds are clearly marked
zencoder.ai
. Block merges until tests pass and CI is green
zencoder.ai
.

Promote pair programming when onboarding new developers or tackling complex sections of the code
amberwilson.co.uk
. Collaboration helps catch issues early and spreads knowledge.

Summary
Modifying a software system is a careful process. Always start by understanding the existing code and context, plan your changes thoughtfully, and prefer minimal, well‑tested fixes over large rewrites. Keep working code intact, document your assumptions, and provide clear, minimal patches. Combined with automated tests and code reviews, these practices will help ensure that Claude makes reliable changes that improve the codebase without breaking it.