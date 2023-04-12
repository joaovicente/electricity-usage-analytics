# electricity-usage-analytics


## Run locally on windows
```bash
python electricity_usage_extraction.py -u bob@gmail.com -p mypassword -d 2023-04-06 --catchup
```


## Executing httpbin_collector in docker
see https://github.com/umihico/docker-selenium-lambda and https://stackoverflow.com/questions/71746654/how-do-i-add-selenium-chromedriver-to-an-aws-lambda-function
```sh
# Build docker image 
docker build -t joao/selenium-python .
# Run script in docker image
docker run -it --entrypoint python joao/selenium-python httpbin_collector.py
```