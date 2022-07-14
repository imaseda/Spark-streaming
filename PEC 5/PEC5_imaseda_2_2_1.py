import findspark
findspark.init()

from pyspark import SparkConf, SparkContext, SQLContext
from pyspark.sql import SparkSession
from pyspark.sql.functions import window

conf = SparkConf()
conf.setMaster("local[1]")
sc = SparkContext(conf=conf)
sqlContext = SQLContext(sc)

sqlContext.setConf("spark.sql.shuffle.partitions", "5")

spark = SparkSession \
    .builder \
    .appName("PEC5_imaseda") \
    .getOrCreate()

rates = spark\
    .readStream\
    .format('rate')\
    .option("rowsPerSecond", 1)\
    .load()
#    .option("rampUpTime", 5)\

windowedCounts = rates\
    .withWatermark("timestamp", "10 seconds") \
    .groupBy(
        window("timestamp", "10 seconds", "5 seconds"),
        rates.value 
    ).count()

query = windowedCounts\
    .writeStream\
    .trigger(processingTime='5 seconds')\
    .format("console") \
    .queryName("count") \
    .option("truncate", "false")\
    .start()

query.awaitTermination() 