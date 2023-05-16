FROM python:3

WORKDIR /app
RUN pip3 install flask
ENTRYPOINT ["python3"]
CMD ["app.py"]
