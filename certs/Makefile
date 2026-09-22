HOSTNAME ?= "localhost,127.0.0.1,action-server-grpc-tls,action-server-https"
CERT_DEST ?= ../integration_tests/grpc_server/setup/certs

install-cfssl-mac-os: ## install cfssl on mac os
	brew install cfssl

install-cfssl-ubuntu: ## install cfssl on ubuntu
	sudo apt install -y golang-cfssl

generate-ca: ## generate ca
	 cfssl gencert \
 		-initca config/ca-csr.json \
 		| cfssljson -bare ca

generate-client-cert: generate-ca  ## generate client cert
	cfssl gencert \
		-ca=ca.pem \
		-ca-key=ca-key.pem \
		-config=config/ca-config.json \
		config/client-csr.json | \
		cfssljson -bare client

generate-server-cert: generate-ca  ## generate server cert
	cfssl gencert \
		-ca=ca.pem \
		-ca-key=ca-key.pem \
		-config=config/ca-config.json \
		-hostname=$(HOSTNAME) \
		config/server-csr.json | \
		cfssljson -bare server

generate-certs: generate-ca generate-client-cert generate-server-cert ## generate client and server certs

install-certs: generate-certs ## copy generated certs into the integration-test fixtures
	cp ca.pem ca-key.pem client.pem client-key.pem server.pem server-key.pem $(CERT_DEST)

