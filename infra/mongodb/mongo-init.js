db.createUser(
        {
            user: "wildsearch_mongo_user",
            pwd: "wildsearch_mongo_password",
            roles: [
                {
                    role: "readWrite",
                    db: "wildsearch_mongo_db"
                }
            ]
        }
);