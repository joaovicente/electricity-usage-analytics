# electricity-usage-analytics

## Run locally on windows
```bash
# persist in filesystem
$ python electricity_usage_collector.py -u username -p password -s ./local_storage
# persist in S3
$ python electricity_usage_collector.py -u username -p password -s s3://jdvhome-dev-data/raw-landing/energia/usage-timeseries
```

## Executing httpbin_collector in docker
see https://github.com/umihico/docker-selenium-lambda and https://stackoverflow.com/questions/71746654/how-do-i-add-selenium-chromedriver-to-an-aws-lambda-function

```bash
# Build docker image 
$ docker build -t joao/selenium-python .
```

```bash
# Run script in docker image using filesystem persistence
$ docker run -v %cd%\docker_storage:/var/local_storage -it --entrypoint python joao/selenium-python electricity_usage_collector.py -u username -p password -s /var/local_storage

# Run script in docker image using S3 persistence
$ docker run -v %cd%\docker_storage:/var/local_storage --env-file tmp\env_file -it --entrypoint python joao/selenium-python electricity_usage_collector.py -u username -p password -s s3://jdvhome-dev-data/raw-landing/energia/usage-timeseries

# Run script in docker image without storing extracted data
$ docker run -v %cd%\docker_storage:/var/local_storage --env-file tmp\env_file -it --entrypoint python joao/selenium-python electricity_usage_collector.py -u username -p password --dry-run

# Where tmp\envfile contains
#AWS_ACCESS_KEY_ID=...
#AWS_SECRET_ACCESS_KEY=...
```

## Other useful commands
```bash
# Also available is a simpler script to validate webdriver
docker run -it --entrypoint python joao/selenium-python httpbin_collector.py

# To inspect contents of the docker image
docker run -it --entrypoint /bin/bash joao/selenium-python
```
