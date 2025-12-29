from pymongo import MongoClient

client = MongoClient(
    "mongodb+srv://alimuldev:holowellness123@cluster0.6ogkj.mongodb.net/db_holo_wellness?retryWrites=true&w=majority&appName=Cluster0",
    tls=True,
    tlsAllowInvalidCertificates=True  # TEMP: disables cert checks
)

print(client.list_database_names())
