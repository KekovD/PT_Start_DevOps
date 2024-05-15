FROM postgres:14-alpine

ENV POSTGRES_USER=replication_user
ENV POSTGRES_PASSWORD=replication_user_password
ENV POSTGRES_DB=postgres
ENV POSTGRES_HOST=db_image
ENV PG_PORT=5432
ENV DATA_DIR_PERM=0700

RUN cat > /init.sh <<EOF
#!/bin/bash

rm -rf /var/lib/postgresql/data/*

until PGPASSWORD=$POSTGRES_PASSWORD pg_basebackup --pgdata=/var/lib/postgresql/data -R --slot=replication_slot --username=$POSTGRES_USER --host=$POSTGRES_HOST --port=$PG_PORT; do
  echo 'Waiting for primary to connect...'
  sleep 1s
done

psql -h $POSTGRES_HOST -U $POSTGRES_USER -d $POSTGRES_DB -c "SELECT * FROM pg_create_physical_replication_slot('replication_slot');"

echo 'Backup done, starting replica...'
chmod $DATA_DIR_PERM /var/lib/postgresql/data
postgres
EOF

RUN chmod +x /init.sh

USER postgres

CMD ["/init.sh"]
