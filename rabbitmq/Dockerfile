# Use the official image with the management plugin installed
FROM rabbitmq:3.12-management

# Copy our configuration and definitions
COPY rabbitmq.conf /etc/rabbitmq/rabbitmq.conf
COPY definitions.json /etc/rabbitmq/definitions.json

# Fix permissions to ensure RabbitMQ can read the files
RUN chown rabbitmq:rabbitmq /etc/rabbitmq/rabbitmq.conf /etc/rabbitmq/definitions.json

# Expose ports
# 5672: Standard AMQP protocol port
# 15672: Web Management UI port
EXPOSE 5672 15672

CMD ["rabbitmq-server"]