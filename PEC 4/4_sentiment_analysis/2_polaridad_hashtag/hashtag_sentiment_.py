import json
import re
import findspark
from textblob import TextBlob

findspark.init()
from pyspark import SparkContext
from pyspark.streaming import StreamingContext
from pyspark.streaming.flume import FlumeUtils
from pyspark.sql import Row, SparkSession


sc = SparkContext(appName="FlumeStreaming", master="local[2]")
sc.setLogLevel("ERROR")

ssc = StreamingContext(sc, 5)
ssc.checkpoint("checkpoint")
kvs = FlumeUtils.createStream(ssc, "localhost", 20033)

def updateFunc(new_values, last_sum):
    if last_sum:
        if len(new_values)!=0:
            new_polarity = (new_values[0][0] + last_sum[0])/2
            new_subjectivity = (new_values[0][1] + last_sum[1])/2
            new_count = new_values[0][2] + last_sum[2]
            return (new_polarity, new_subjectivity, new_count)
        else:
            return (last_sum[0], last_sum[1], last_sum[2])

    else:
        new_polarity = new_values[0][0]
        new_subjectivity = new_values[0][1]
        new_count = new_values[0][2]
        return (new_polarity, new_subjectivity, new_count)
        

def tweet_info(tweet):
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
    temp = re.sub(r"http\S+", " ", temp)
    temp = re.sub(r"www.\S+", " ", temp)
    hashtags = re.findall("#[A-Za-z0-9_]+", temp)
    temp = re.sub("#[A-Za-z0-9_]+"," ", temp)
    temp = temp.split()
    temp = [w.strip() for w in temp]
    temp = " ".join(word for word in temp)
    if hashtags:
        for i in hashtags:
            return [(i, (TextBlob(temp).sentiment.polarity, TextBlob(temp).sentiment.subjectivity, 1))]

def getSparkSessionInstance(sparkConf):
    if ('sparkSessionSingletonInstance' not in globals()):
        globals()['sparkSessionSingletonInstance'] = SparkSession\
            .builder\
            .config(conf=sparkConf)\
            .getOrCreate()
    return globals()['sparkSessionSingletonInstance']


def process(time, rdd):
    print("========= %s =========" % str(time))

    spark = getSparkSessionInstance(rdd.context.getConf())

    rowRdd = rdd.map(lambda w: Row(hashtag=w[0], polarity=w[1][0], subjectivity=w[1][1], count=w[1][2]))
    if rowRdd.isEmpty() == False:
        wordsDataFrame = spark.createDataFrame(rowRdd)

        wordsDataFrame.createOrReplaceTempView("tweets")

        wordCountsDataFrame = \
            spark.sql("select hashtag, polarity, subjectivity, count from tweets order by count desc")
        wordCountsDataFrame.show(10)


tweets = kvs.filter(lambda x: json.loads(x[1])['lang'] == "en")\
            .map(lambda x: json.loads(x[1])['text'])

hashtags = tweets.filter(lambda x : re.search(r'#\w+', x, flags=re.U))\
                .flatMap(lambda x: tweet_info(x))\
                .updateStateByKey(updateFunc)

#if (hashtags.count() != 0):
#    hashtags = hashtags.transform(lambda rdd: rdd.sortBy(lambda x: x[1][2], ascending=False))

hashtags.foreachRDD(process)



ssc.start()
ssc.awaitTermination()



