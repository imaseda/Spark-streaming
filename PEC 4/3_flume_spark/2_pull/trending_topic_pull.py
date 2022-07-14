import json
import findspark
import re
findspark.init()

from pyspark import SparkContext
from pyspark.streaming import StreamingContext
from pyspark.streaming.flume import FlumeUtils


sc = SparkContext(appName="FlumeStreaming", master="local[2]")
sc.setLogLevel("ERROR")

ssc = StreamingContext(sc, 5)
ssc.checkpoint("checkpoint")
address = [("localhost", 20033)]
kvs = FlumeUtils.createPollingStream(ssc, address, maxBatchSize=10, parallelism=2)

def updateFunc(new_values, last_sum):
    return sum(new_values) + (last_sum or 0)

#flatMap(lambda x: re.sub('[^a-zA-Z0-9# ]', '', x.strip()))
lines = kvs.map(lambda x: json.loads(x[1])['text'])
counts = lines.flatMap(lambda line: re.sub('[^a-zA-Z0-9#_ ]', ' ', line.strip(), flags=re.U).split())\
              .filter(lambda x : re.findall(r'#\w+', x, flags=re.U))\
              .map(lambda word: (word, 1)) \
              .updateStateByKey(updateFunc)

sorted_counts = counts.transform(lambda rdd: rdd.sortBy(lambda x: x[1], ascending=False))
sorted_counts.pprint()

ssc.start()
ssc.awaitTermination()
