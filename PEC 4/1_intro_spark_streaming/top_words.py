import findspark
findspark.init()

from pyspark import SparkContext
from pyspark.streaming import StreamingContext

# Cambiad el username por vuestro nombre de usuario
sc = SparkContext("local[2]", "top_words_imaseda")
sc.setLogLevel("ERROR")

ssc = StreamingContext(sc, 5)
ssc.checkpoint("checkpoint")

def updateFunc(new_values, last_sum):
    return sum(new_values) + (last_sum or 0)


lines = ssc.socketTextStream("localhost", 20033)

wordCounts = lines.flatMap(lambda line: line.split(" "))\
                  .map(lambda word: (word, 1))\
                  .updateStateByKey(updateFunc)

wordCounts = wordCounts.transform(lambda rdd: rdd.sortBy(lambda x: x[1], ascending=False))
wordCounts.pprint()

ssc.start()
ssc.awaitTermination()
