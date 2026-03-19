.PHONY: bootstrap install-py install-ts dev-py dev-ts deploy-py deploy-ts clean

##= Installation

bootstrap: install-py install-ts

install-py:
	cd graphs/python && uv sync --dev

install-ts:
	cd graphs/typescript && pnpm install

##= Development (local LangGraph dev server)

dev-py:
	uv run --directory graphs/python langgraph dev --config langgraph.json --no-browser --n-jobs-per-worker 10

dev-ts:
	npx --prefix graphs/typescript @langchain/langgraph-cli dev --config langgraph.ts.json --no-browser --n-jobs-per-worker 10

##= Deployment

deploy-py:
	uv run --directory graphs/python langgraph deploy --config langgraph.json

deploy-ts:
	npx --prefix graphs/typescript @langchain/langgraph-cli deploy --config langgraph.ts.json

##= Utilities

clean:
	rm -rf graphs/python/.venv
	rm -rf graphs/typescript/node_modules
	rm -rf graphs/typescript/dist
