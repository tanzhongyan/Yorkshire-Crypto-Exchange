# Use the official PostgreSQL image
FROM postgres:latest

COPY create-multiple-postgresql-databases.sh /docker-entrypoint-initdb.d/

RUN chmod +x /docker-entrypoint-initdb.d/create-multiple-postgresql-databases.sh

EXPOSE 5432