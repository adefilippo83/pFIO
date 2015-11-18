FROM debian:jessie

RUN mkdir /app
ADD run_fio.py /app/
ADD requirements.txt /app/
WORKDIR /app
RUN apt-get update
RUN apt-get -y install python
RUN apt-get -y install python-pip
RUN apt-get -y install libcurl4-gnutls-dev
RUN apt-get -y install libpython2.7-dev
RUN pip install -r requirements.txt
RUN python run_fio.py -u
RUN chmod 755 /app/run_fio.py
ENTRYPOINT /app/run_fio.py
