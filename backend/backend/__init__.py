import mongoengine


try:# Disconnect previous default connection (prevents "already registered" errors)
    mongoengine.disconnect(alias="default")
except:
    pass

# Connect to MongoDB
mongoengine.connect(
    db="learnloop_db",    # MongoDB database name
    host="localhost",     # MongoDB host
    port=27017,           # default port
    alias="default"
)

print("MongoEngine connected!")