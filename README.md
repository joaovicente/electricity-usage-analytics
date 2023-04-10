# electricity-usage-analytics


## Run locally on windows
```bash
python electricity_usage_extraction.py -u bob@gmail.com -p mypassword -d 2023-04-06 --catchup
```


## Executing httpbin_collector in docker
see https://github.com/umihico/docker-selenium-lambda and https://stackoverflow.com/questions/71746654/how-do-i-add-selenium-chromedriver-to-an-aws-lambda-function
```sh
# Build docker image https://stackify.com/docker-build-a-beginners-guide-to-building-docker-images/
docker build -t joao/selenium-python .
docker run -it --entrypoint /bin/bash joao/selenium-python
python3 ./httpbin_collector.py
```