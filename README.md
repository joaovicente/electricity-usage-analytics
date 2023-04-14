# electricity-usage-analytics

## Run locally on windows
```bash
python electricity_usage_collector.py -u username -p password -s ./local_storage
```

## Executing httpbin_collector in docker
see https://github.com/umihico/docker-selenium-lambda and https://stackoverflow.com/questions/71746654/how-do-i-add-selenium-chromedriver-to-an-aws-lambda-function

```sh
# Build docker image 
docker build -t joao/selenium-python .

# Run script in docker image
docker run -v %cd%\docker_storage:/var/local_storage -it --entrypoint python joao/selenium-python electricity_usage_collector.py -u username -p password -s /var/local_storage

# Also available is a simpler script to validate webdriver
docker run -it --entrypoint python joao/selenium-python httpbin_collector.py

# To inspect contents of the docker image
docker run -it --entrypoint /bin/bash joao/selenium-python
```
