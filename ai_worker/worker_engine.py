import os
import time
import json
import logging
import pika
import sys
import agent

# --- Global Logger Config ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
main_logger = logging.getLogger("WorkerEngine")

# --- RabbitMQ Config ---
RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "ai-message-broker")
RABBITMQ_USER = os.getenv("RABBITMQ_USER", "guest")
RABBITMQ_PASS = os.getenv("RABBITMQ_PASS", "guest")

EXCHANGE_NAME = "ai_system_exchange"
REQUEST_QUEUE = "request_queue"
RESULT_ROUTING_KEY = "result"

class JobLoggerAdapter(logging.LoggerAdapter):
    """
    Prefixes all log messages with the specific Job ID.
    """
    def process(self, msg, kwargs):
        return '[Job: %s] %s' % (self.extra['job_id'], msg), kwargs

def get_rabbitmq_connection():
    credentials = pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASS)
    parameters = pika.ConnectionParameters(
        host=RABBITMQ_HOST, 
        credentials=credentials,
        heartbeat=600,
        blocked_connection_timeout=300
    )
    return pika.BlockingConnection(parameters)

def main():
    connection = None
    while not connection:
        try:
            connection = get_rabbitmq_connection()
            main_logger.info("Connected to RabbitMQ.")
        except pika.exceptions.AMQPConnectionError:
            main_logger.warning("RabbitMQ unavailable. Retrying in 5s...")
            time.sleep(5)

    channel = connection.channel()

    # Ensure infrastructure exists
    channel.queue_declare(queue=REQUEST_QUEUE, durable=True)
    channel.exchange_declare(exchange=EXCHANGE_NAME, exchange_type='direct', durable=True)

    def callback(ch, method, properties, body):
        try:
            message = json.loads(body)
            job_id = message.get("job_id", "unknown")
            
            # Create custom logger for this job instance
            job_logger = JobLoggerAdapter(main_logger, {'job_id': job_id})
            job_logger.info("Received new task.")

            # --- DELEGATE TO INTELLIGENCE LAYER ---
            result_payload = agent.process_request(message, job_logger)
            # --------------------------------------

            # Publish Result
            ch.basic_publish(
                exchange=EXCHANGE_NAME,
                routing_key=RESULT_ROUTING_KEY,
                body=json.dumps(result_payload),
                properties=pika.BasicProperties(delivery_mode=2) 
            )
            
            job_logger.info(f"Result published to '{RESULT_ROUTING_KEY}'.")
            
            # Ack
            ch.basic_ack(delivery_tag=method.delivery_tag)

        except Exception as e:
            main_logger.error(f"Critical Worker Error: {e}")
            # Negative Ack (do not requeue to prevent loops)
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

    channel.basic_qos(prefetch_count=1)
    channel.basic_consume(queue=REQUEST_QUEUE, on_message_callback=callback)

    main_logger.info("Worker is listening for tasks...")
    channel.start_consuming()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        try:
            sys.exit(0)
        except SystemExit:
            os._exit(0)
