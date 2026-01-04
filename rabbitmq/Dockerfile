FROM rabbitmq:3.12-management

# Copy config files
COPY rabbitmq.conf /etc/rabbitmq/rabbitmq.conf
COPY definitions.json /etc/rabbitmq/definitions.json

# Fix permissions so RabbitMQ can read them
RUN chown rabbitmq:rabbitmq /etc/rabbitmq/rabbitmq.conf /etc/rabbitmq/definitions.json

EXPOSE 5672 15672
CMD ["rabbitmq-server"]