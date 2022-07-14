import json
import re
from textblob import TextBlob
import findspark
findspark.init()

from pyspark import SparkContext
from pyspark.streaming import StreamingContext
from pyspark.streaming.flume import FlumeUtils


sc = SparkContext(appName="FlumeStreaming", master="local[2]")
sc.setLogLevel("ERROR")

ssc = StreamingContext(sc, 5)
ssc.checkpoint("checkpoint")
kvs = FlumeUtils.createStream(ssc, "localhost", 20033)

def updateFunc(new_values, last_sum):
    return sum(new_values) + (last_sum or 0)

def clean_tweet(tweet):
    emoji_pattern = re.compile("["
        u"\U0001F600-\U0001F64F"  # emoticons
        u"\U0001F300-\U0001F5FF"  # symbols & pictographs
        u"\U0001F680-\U0001F6FF"  # transport & map symbols
        u"\U0001F1E0-\U0001F1FF"  # flags (iOS)
        u"\U0001F1F2-\U0001F1F4"  # Macau flag
        u"\U0001F1E6-\U0001F1FF"  # flags
        u"\U0001F600-\U0001F64F"
        u"\U00002702-\U000027B0"
        u"\U000024C2-\U0001F251"
        u"\U0001f926-\U0001f937"
        u"\U00010000-\U0010ffff"
        u"\U00002500-\U00002BEF"
        u"\U0001F1F2"
        u"\U0001F1F4"
        u"\U0001F620"
        u"\u200d"
        u"\u23cf"
        u"\u23e9"
        u"\u231a"
        u"\ufe0f"
        u"\u3030"
        u"\u2640-\u2642"
        u"\u2600-\u2B55"
        "]+", flags=re.UNICODE)
    
    temp = emoji_pattern.sub(r' ', tweet)
    temp = re.sub("@[A-Za-z0-9_]+"," ", temp)
    temp = re.sub("#[A-Za-z0-9_]+"," ", temp)
    temp = re.sub(r"http\S+", " ", temp)
    temp = re.sub(r"www.\S+", " ", temp)
    temp = temp.split()
    temp = [w.strip() for w in temp]
    temp = " ".join(word for word in temp)
    return temp

def polarity_transform(text):
    p = TextBlob(text).sentiment.polarity
    if p < 0:
        return ("negative", 1)
    elif p > 0:
        return ("positive", 1) 
    else:
        return ("neutral", 1)


counts = kvs.filter(lambda x: json.loads(x[1])['lang'] == "en")\
           .map(lambda x: polarity_transform(clean_tweet(json.loads(x[1])['text'])))\
           .reduceByKeyAndWindow(lambda x, y: x + y, lambda x, y: x - y, 90, 5)


sorted_counts = counts.transform(lambda rdd: rdd.sortBy(lambda x: x[1], ascending=False))
sorted_counts.pprint()


ssc.start()
ssc.awaitTermination()
