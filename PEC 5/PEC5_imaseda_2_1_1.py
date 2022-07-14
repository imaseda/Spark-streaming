import findspark
findspark.init()

from pyspark import SparkConf, SparkContext, SQLContext, HiveContext
from pyspark.sql import SparkSession
from pyspark.sql.functions import explode
from pyspark.sql.functions import split

conf = SparkConf()
conf.setMaster("local[1]")
sc = SparkContext(conf=conf)
print(sc.version)

spark = SparkSession \
    .builder \
    .appName("PEC5_imaseda") \
    .getOrCreate()

linesDF = spark\
    .readStream\
    .format('socket')\
    .option('host', 'localhost')\
    .option('port', 20033)\
    .load()

wordsDF = linesDF.select(
    explode(
        split(linesDF.value, ' ')
    ).alias('palabra')
)

wordCountsDF = wordsDF.filter(wordsDF.palabra.startswith('A'))\
                      .groupBy('palabra')\
                      .count()\
                      .where('count > 5')

query = wordCountsDF\
    .writeStream\
    .outputMode('complete')\
    .format("console") \
    .queryName("palabras") \
    .start()

query.awaitTermination() 