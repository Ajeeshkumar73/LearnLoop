from mongoengine import connect

connect(
    db="learnloop_db",
    host="mongodb://localhost:27017/learnloop_db"
)
