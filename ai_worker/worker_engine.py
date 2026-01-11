import os
import time
import json
import logging
import pika
import agent

# Configure Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Config
RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "ai-message-broker")
RABBITMQ_USER = os.getenv("RABBITMQ_USER", "guest")
RABBITMQ_PASS = os.getenv("RABBITMQ_PASS", "guest")

# Constants from your definitions.json
EXCHANGE_NAME = "ai_system_exchange"
REQUEST_QUEUE = "request_queue"
RESULT_ROUTING_KEY = "result" 

def get_connection():
    credentials = pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASS)
    parameters = pika.ConnectionParameters(host=RABBITMQ_HOST, credentials=credentials)
    return pika.BlockingConnection(parameters)

def main():
    connection = None
    while not connection:
        try:
            connection = get_connection()
            logger.info("Successfully connected to RabbitMQ!")
        except pika.exceptions.AMQPConnectionError:
            logger.warning("RabbitMQ not ready yet, retrying in 5 seconds...")
            time.sleep(5)

    channel = connection.channel()
    
    # Ensure infrastructure exists
    channel.queue_declare(queue=REQUEST_QUEUE, durable=True)
    channel.exchange_declare(exchange=EXCHANGE_NAME, exchange_type='direct', durable=True)

    def callback(ch, method, properties, body):
        try:
            message = json.loads(body)
            
            # 1. Run the Agent Logic
            result_data = agent.process_request(message)
            
            # 2. Publish Result
            ch.basic_publish(
                exchange=EXCHANGE_NAME,
                routing_key=RESULT_ROUTING_KEY,
                body=json.dumps(result_data),
                properties=pika.BasicProperties(
                    delivery_mode=2,  # Make message persistent
                )
            )
            logger.info(f"Published result for Job {result_data.get('job_id')} to '{RESULT_ROUTING_KEY}'")

            # 3. Acknowledge original request
            ch.basic_ack(delivery_tag=method.delivery_tag)

        except Exception as e:
            logger.error(f"Critical Worker Error: {e}")
            # Reject and do NOT requeue (to prevent infinite error loops on bad data)
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

    channel.basic_qos(prefetch_count=1)
    channel.basic_consume(queue=REQUEST_QUEUE, on_message_callback=callback)

    logger.info(" [*] Worker AI Listening...")
    channel.start_consuming()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        try:
            sys.exit(0)
        except SystemExit:
            os._exit(0)