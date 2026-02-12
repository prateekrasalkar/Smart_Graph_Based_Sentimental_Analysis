from neo4j import GraphDatabase, exceptions
import logging
import traceback
import backoff


# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


class Neo4jHandler:
    def __init__(self, uri, max_retry_time=30):
        self.uri = uri
        self.driver = None
        self.max_retry_time = max_retry_time
        self.connect()

    @backoff.on_exception(
        backoff.expo,
        (exceptions.ServiceUnavailable, exceptions.SessionExpired),
        max_time=30,
    )
    def connect(self):
        if self.driver is None:
            try:
                self.driver = GraphDatabase.driver(self.uri)
                self.check_connection()
            except Exception as e:
                logging.error(f"Failed to connect to Neo4j: {str(e)}")
                raise

    def ensure_connection(self):
        try:
            if self.driver is None:
                self.connect()
            self.check_connection()
        except Exception:
            self.close()
            self.connect()

    def check_connection(self):
        try:
            with self.driver.session() as session:
                result = session.run("RETURN 1")
                result.single()
                logging.info("Successfully connected to Neo4j!")
        except Exception as e:
            logging.error(f"Connection check failed: {str(e)}")
            self.close()
            raise

    def close(self):
        if self.driver:
            try:
                self.driver.close()
            except Exception as e:
                logging.error(f"Error closing connection: {str(e)}")
            finally:
                self.driver = None

    # ================= USER =================

    def create_user(self, user_id, name):
        self.ensure_connection()

        query = """
        MERGE (u:User {user_id: $user_id})
        ON CREATE SET u.name = $name
        ON MATCH SET u.name = $name
        RETURN u
        """

        with self.driver.session() as session:
            result = session.run(query, user_id=user_id, name=name)
            return result.single()

    def get_all_users(self):
        self.ensure_connection()

        query = """
        MATCH (u:User)
        RETURN u.user_id AS user_id, u.name AS name
        ORDER BY u.name
        """

        with self.driver.session() as session:
            result = session.run(query)
            return [dict(record) for record in result]

    # ================= POSTS =================

    def create_post(self, user_id, content):
        self.ensure_connection()

        sentiment = self._analyze_sentiment(content)

        query = """
        MATCH (u:User {user_id: $user_id})
        CREATE (p:Post {
            post_id: randomUUID(),
            content: $content,
            sentiment: $sentiment,
            timestamp: datetime()
        })-[:POSTED_BY]->(u)
        WITH p
        SET p.timestamp = toString(p.timestamp)
        RETURN p
        """

        with self.driver.session() as session:
            result = session.run(
                query,
                user_id=user_id,
                content=content,
                sentiment=sentiment,
            )
            record = result.single()

            if record is None:
                raise Exception(f"User with ID {user_id} not found")

        # Update relationships after post creation
        self._update_relationships()

        return {"p": record["p"]}

    def get_user_posts(self, user_id):
        self.ensure_connection()

        query = """
        MATCH (p:Post)-[:POSTED_BY]->(u:User {user_id: $user_id})
        RETURN p.post_id AS post_id,
               p.content AS content,
               p.sentiment AS sentiment,
               p.timestamp AS timestamp
        ORDER BY p.timestamp DESC
        """

        with self.driver.session() as session:
            result = session.run(query, user_id=user_id)
            return [dict(record) for record in result]

    def get_recent_posts(self):
        self.ensure_connection()

        query = """
        MATCH (p:Post)-[:POSTED_BY]->(u:User)
        WHERE p.deleted IS NULL
        RETURN p.post_id AS post_id,
               p.content AS content,
               p.sentiment AS sentiment,
               p.timestamp AS timestamp,
               u.name AS user_name,
               u.user_id AS user_id
        ORDER BY p.timestamp DESC
        LIMIT 10
        """

        with self.driver.session() as session:
            result = session.run(query)
            return [dict(record) for record in result]

    # ================= RELATIONSHIPS =================

    def _update_relationships(self):
        try:
            query = """
            MATCH (u:User)
            OPTIONAL MATCH (u)<-[:POSTED_BY]-(p:Post)
            WITH u, COLLECT(p.content) AS contents
            WHERE size(contents) > 0
            RETURN u.user_id AS user_id, contents
            """

            with self.driver.session() as session:
                result = session.run(query)
                users_data = [dict(record) for record in result]

            if len(users_data) < 2:
                return

            # Combine all posts of each user
            user_contents = {
                user["user_id"]: " ".join(filter(None, user["contents"]))
                for user in users_data
            }

            # Convert to word sets
            user_words = {
                user_id: set(content.lower().split())
                for user_id, content in user_contents.items()
            }

            # Remove old relationships
            self._clear_relationships()

            relationships = []
            min_common_words =1

            user_ids = list(user_words.keys())

            for i in range(len(user_ids)):
                for j in range(i + 1, len(user_ids)):
                    common = user_words[user_ids[i]].intersection(
                        user_words[user_ids[j]]
                    )

                    if len(common) >= min_common_words:
                        relationships.append((user_ids[i], user_ids[j]))
                        relationships.append((user_ids[j], user_ids[i]))

            if relationships:
                self._create_relationships(relationships)

        except Exception as e:
            logger.error(f"Error updating relationships: {str(e)}")
            logger.error(traceback.format_exc())

    def _clear_relationships(self):
        query = "MATCH ()-[r:SIMILAR_CONTENT]->() DELETE r"
        with self.driver.session() as session:
            session.run(query)

    def _create_relationships(self, relationships):
        query = """
        UNWIND $relationships AS rel
        MATCH (u1:User {user_id: rel[0]})
        MATCH (u2:User {user_id: rel[1]})
        MERGE (u1)-[:SIMILAR_CONTENT]->(u2)
        """
        with self.driver.session() as session:
            session.run(query, {"relationships": relationships})

    # ================= SENTIMENT =================

    def _analyze_sentiment(self, content):
        positive_words = {
            "good", "great", "awesome", "excellent",
            "happy", "love", "wonderful", "amazing"
        }

        negative_words = {
            "bad", "terrible", "awful", "hate",
            "sad", "angry", "poor"
        }

        words = content.lower().split()

        pos_count = sum(1 for w in words if w in positive_words)
        neg_count = sum(1 for w in words if w in negative_words)

        if pos_count > neg_count:
            return "positive"
        elif neg_count > pos_count:
            return "negative"
        return "neutral"
