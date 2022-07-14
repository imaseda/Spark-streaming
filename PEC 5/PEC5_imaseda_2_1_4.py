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
    .load()
#    .option('includeTimestamp', 'true')\

wordsDF = linesDF.select(
    explode(
        split(linesDF.value, ' ')
    ).alias('palabra')
)

wordsDF.createOrReplaceTempView("palabras")

sqlDF = spark.sql("SELECT * FROM palabras")

query = sqlDF\
    .writeStream\
    .trigger(processingTime='5 seconds')\
    .outputMode('update')\
    .format("console") \
    .queryName("palabras") \
    .option("truncate", "false")\
    .start()

query.awaitTermination() 