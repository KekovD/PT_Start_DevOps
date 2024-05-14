FROM python

COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt --no-cache-dir

COPY . .

CMD ["python", "bot.py"]
