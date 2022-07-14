import findspark
findspark.init()

from pyspark import SparkConf, SparkContext, SQLContext
from pyspark.sql import SparkSession
from pyspark.sql.functions import explode
from pyspark.sql.functions import split

conf = SparkConf()
conf.setMaster("local[1]")
sc = SparkContext(conf=conf)
sqlContext = SQLContext(sc)

spark = SparkSession \
    .builder \
    .appName("FlightsInformation") \
    .getOrCreate()

flights= spark \
    .readStream \
    .format("socket") \
    .option("host", "localhost") \
    .option("port", 20033) \
    .load()

flights_information= flights
flights_information.printSchema()

query = flights_information\
    .writeStream \
    .outputMode("append") \
    .format("console") \
    .option("truncate", "false")\
    .start()

query.awaitTermination()