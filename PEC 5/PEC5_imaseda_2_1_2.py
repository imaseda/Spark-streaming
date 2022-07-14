import findspark
findspark.init()

from pyspark import SparkConf, SparkContext, SQLContext, HiveContext
from pyspark.sql import SparkSession
from pyspark.sql.functions import explode
from pyspark.sql.functions import split
from pyspark.sql.functions import current_timestamp, col


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
    .option('includeTimestamp', 'true')\
    .load()

wordsDF = linesDF.select(
    explode(
        split(linesDF.value, ' ')
    ).alias('palabra'), linesDF.timestamp
)

wordsDF.createOrReplaceTempView("palabras")

sqlDF = spark.sql("SELECT palabra, timestamp as tiempo FROM palabras WHERE LENGTH(palabra) > 3")

query = sqlDF\
    .writeStream\
    .format("console") \
    .option("checkpointLocation", "hdfs://Cloudera01:8020/user/imaseda/punto_control_pec5")\
    .queryName("palabras") \
    .start()

query.awaitTermination() 