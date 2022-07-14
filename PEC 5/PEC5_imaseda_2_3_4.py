import findspark
findspark.init()

from pyspark import SparkConf, SparkContext, SQLContext
from pyspark.sql import SparkSession
from pyspark.sql.functions import from_json, col
from pyspark.sql.types import *

conf = SparkConf()
conf.setMaster("local[1]")
sc = SparkContext(conf=conf)
sqlContext = SQLContext(sc)

sqlContext.setConf("spark.sql.shuffle.partitions", "4")

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

schema = StructType([ \
    StructField("longitude", DoubleType(), True),
    StructField("callsign", StringType(), True),
    StructField("vertical_rate", DoubleType(), True),
    StructField("velocity", DoubleType(), True),
    StructField("country", StringType(), True),
    StructField("latitude", DoubleType(), True)
    ])



flights_information =flights.withColumn("value", from_json("value", schema))\
                       .select(col('value.*'))

flights_agg = flights_information.select(col('country'))\
                                .groupBy('country')\
                                .count()


query = flights_agg\
    .writeStream \
    .outputMode("complete") \
    .format("console") \
    .option("truncate", "false")\
    .start()

query.awaitTermination()