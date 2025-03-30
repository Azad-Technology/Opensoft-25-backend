from neo4j import GraphDatabase
from pathlib import Path
import json
import os
from dotenv import load_dotenv

load_dotenv()

NEO4J_URI = os.getenv('NEO4J_URI')
NEO4J_USER = os.getenv('NEO4J_USERNAME')
NEO4J_PASSWORD = os.getenv('NEO4J_PASSWORD')


question_bank = Path(__file__).resolve().parent.parent / "analysis" / "data" / "tagged_questions.json"
question_relations = Path(__file__).resolve().parent.parent / "analysis" / "data" / "question_relationships.json"


class Neo4jUploader:
    def __init__(self, uri, user, password):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
    
    def close(self):
        self.driver.close()
    
    # To be run once: Uploads the entire data to neo4j
    def upload_data(self, data, relationships):
        with self.driver.session() as session:
            print('Uploading questions...')
            for record in data:
                session.execute_write(self._create_node, record)
            print('Questions uploaded')
            print('Creating relations...')
            for relationship in relationships:
                session.execute_write(self._create_relationship, relationship)
            print('Relations created')

    def get_questions_by_tag(self, tag):
        with self.driver.session() as session:
            result = session.execute_read(self._query_questions_by_tag, tag)
            return result
    
    def get_related_questions(self, node_id, threshold):
        with self.driver.session() as session:
            result = session.execute_read(self._query_related_questions, node_id, threshold)
            return result
        

    @staticmethod
    def _query_related_questions(tx, node_id, threshold):
        query = """
        MATCH (q1:Question {id: $node_id})-[r:RELATED_TO]->(q2:Question)
        WHERE r.score > $threshold
        RETURN q2.id, q2.question, r.score
        """
        result = tx.run(query, node_id=node_id, threshold=threshold)
        return [record for record in result]

    #function to get questions based on tag , threshold_score , node_depth
    '''
        [
            {
                question :
                related_questions: [
                    {
                        question: [
                            related_questions : 
                        ]
                    }
                ]
            }
        ]
    '''

    @staticmethod
    def _query_questions_by_tag(tx, tag):
        query = """
        MATCH (q:Question)
        WHERE $tag IN q.tags
        RETURN q.id, q.question, q.tags
        """
        result = tx.run(query, tag=tag)
        return [record for record in result]        
    
    @staticmethod
    def _create_node(tx , record):
        query = (
            "CREATE (n:Question {id: $id, question: $question, tags: $tags})"
        )
        tx.run(query, id=record["id"], question=record["question"], tags=record["tags"])

    @staticmethod
    def _create_relationship(tx , relationship):
        query = (
            "MATCH (q1:Question {id: $from_id}), (q2:Question {id: $to_id})"
            "MERGE (q1)-[r:RELATED_TO {score: $score}]->(q2)"
        )
        tx.run(query, from_id=relationship["from_id"], to_id=relationship["to_id"], score=relationship["score"])




if __name__ == "__main__":

    # Opened csv files
    with open(question_bank, "r", encoding="utf-8") as file:
        tagged_questions = json.load(file)
    
    with open(question_relations, "r", encoding="utf-8")    as file:
        question_relationships = json.load(file)

    # Uploader
    uploader = Neo4jUploader(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)
    # uploader.upload_data(tagged_questions , question_relationships)  TO BE RUN ONCE

    questions = uploader.get_questions_by_tag('Workplace_Conflict')
    print(len(questions))
    uploader.close()
    print("Data uploaded successfully!")


