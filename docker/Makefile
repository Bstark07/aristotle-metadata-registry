prepare_server:
	django-admin migrate
	django-admin compile_and_collect_static
	django-admin load_aristotle_help

metadata:
	curl https://raw.githubusercontent.com/aristotle-mdr/user-documentation/draft/python/server/docs_server/fixtures/users.yaml > /tmp/users.yaml
	curl https://raw.githubusercontent.com/aristotle-mdr/user-documentation/draft/python/server/docs_server/fixtures/test_metadata.yaml > /tmp/metadata.yaml
	django-admin loaddata /tmp/users.yaml
	django-admin loaddata /tmp/metadata.yaml

server:
	sudo docker-compose up

elasticsearch_work:
	sudo sysctl -w vm.max_map_count=262144
esw:
	sudo sysctl -w vm.max_map_count=262144
