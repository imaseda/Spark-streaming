/**
 * Licensed to the Apache Software Foundation (ASF) under one
 * or more contributor license agreements.  See the NOTICE file
 * distributed with this work for additional information
 * regarding copyright ownership.  The ASF licenses this file
 * to you under the Apache License, Version 2.0 (the
 * "License"); you may not use this file except in compliance
 * with the License.  You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

package com.cloudera.flume.source;

import java.util.HashMap;
import java.util.Map;

import org.apache.flume.Context;
import org.apache.flume.Event;
import org.apache.flume.EventDrivenSource;
import org.apache.flume.channel.ChannelProcessor;
import org.apache.flume.conf.Configurable;
import org.apache.flume.event.EventBuilder;
import org.apache.flume.source.AbstractSource;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import twitter4j.FilterQuery;
import twitter4j.StallWarning;
import twitter4j.Status;
import twitter4j.StatusDeletionNotice;
import twitter4j.StatusListener;
import twitter4j.TwitterStream;
import twitter4j.TwitterStreamFactory;
import twitter4j.auth.AccessToken;
import twitter4j.conf.ConfigurationBuilder;
import twitter4j.json.DataObjectFactory;

//Libraries to modify JSON
import org.json.simple.JSONObject;
import org.json.simple.JSONArray;
import org.json.simple.parser.ParseException;
import org.json.simple.parser.JSONParser;

/**
 * A Flume Source, which pulls data from Twitter's streaming API. Currently,
 * this only supports pulling from the sample API, and only gets new status
 * updates.
 */
public class TwitterSource extends AbstractSource
    implements EventDrivenSource, Configurable {

  private static final Logger logger =
      LoggerFactory.getLogger(TwitterSource.class);

  /** Information necessary for accessing the Twitter API */
  private String consumerKey;
  private String consumerSecret;
  private String accessToken;
  private String accessTokenSecret;

  private String[] keywords;

  /** The actual Twitter stream. It's set up to collect raw JSON data */
  private  TwitterStream twitterStream;
  private int num_tweets = 0;

  /**
   * The initialization method for the Source. The context contains all the
   * Flume configuration info, and can be used to retrieve any configuration
   * values necessary to set up the Source.
   */
  @Override
  public void configure(Context context) {
    consumerKey = context.getString(TwitterSourceConstants.CONSUMER_KEY_KEY);
    consumerSecret = context.getString(TwitterSourceConstants.CONSUMER_SECRET_KEY);
    accessToken = context.getString(TwitterSourceConstants.ACCESS_TOKEN_KEY);
    accessTokenSecret = context.getString(TwitterSourceConstants.ACCESS_TOKEN_SECRET_KEY);

    String keywordString = context.getString(TwitterSourceConstants.KEYWORDS_KEY, "");
    if (keywordString.trim().length() == 0) {
        keywords = new String[0];
    } else {
      keywords = keywordString.split(",");
      for (int i = 0; i < keywords.length; i++) {
        keywords[i] = keywords[i].trim();
      }
    }

    ConfigurationBuilder cb = new ConfigurationBuilder();
    cb.setOAuthConsumerKey(consumerKey);
    cb.setOAuthConsumerSecret(consumerSecret);
    cb.setOAuthAccessToken(accessToken);
    cb.setOAuthAccessTokenSecret(accessTokenSecret);
    cb.setJSONStoreEnabled(true);
    cb.setIncludeEntitiesEnabled(true);

    twitterStream = new TwitterStreamFactory(cb.build()).getInstance();
  }

  /**
   * Start processing events. This uses the Twitter Streaming API to sample
   * Twitter, and process tweets.
   */
  @Override
  public void start() {
    // The channel is the piece of Flume that sits between the Source and Sink,
    // and is used to process events.
    final ChannelProcessor channel = getChannelProcessor();

    final Map<String, String> headers = new HashMap<String, String>();

    // The StatusListener is a twitter4j API, which can be added to a Twitter
    // stream, and will execute methods every time a message comes in through
    // the stream.
    StatusListener listener = new StatusListener() {
      // The onStatus method is executed every time a new tweet comes in.
      public void onStatus(Status status) {
        // The EventBuilder is used to build an event using the headers and
        // the raw JSON of a tweet
        if(!status.isRetweet() && status.getInReplyToScreenName()==null){

          //load json file
          String rawJson = DataObjectFactory.getRawJSON(status);
          try{

            JSONObject tweet = (JSONObject) new JSONParser().parse(rawJson);
            JSONObject filtered_tweet = new JSONObject();

            filtered_tweet.put("created_at", tweet.get("created_at"));
            filtered_tweet.put("id", tweet.get("id"));
            filtered_tweet.put("text", tweet.get("text"));
            filtered_tweet.put("source", tweet.get("source"));
            filtered_tweet.put("lang", tweet.get("lang"));
            filtered_tweet.put("filter_level", tweet.get("filter_level"));

            JSONObject user = (JSONObject) tweet.get("user");
            JSONObject filtered_user = new JSONObject();

            filtered_user.put("id", user.get("id"));
            filtered_user.put("screen_name", user.get("screen_name"));
            filtered_user.put("lang", user.get("lang"));
            filtered_user.put("followers_count", user.get("followers_count"));
            filtered_user.put("friends_count", user.get("friends_count"));

            filtered_tweet.put("user", filtered_user);

            headers.put("timestamp", String.valueOf(status.getCreatedAt().getTime()));

            Event event = EventBuilder.withBody(filtered_tweet.toString().getBytes(), headers);

            logger.debug("tweet arrived");
            num_tweets++;

            channel.processEvent(event);

            if (num_tweets >= 200){
              java.lang.System.exit(0);
            }
          }catch(ParseException pe){
            System.out.println("Something went wrong.");
          }
        }
      }

      // This listener will ignore everything except for new tweets
      public void onDeletionNotice(StatusDeletionNotice statusDeletionNotice) {}
      public void onTrackLimitationNotice(int numberOfLimitedStatuses) {}
      public void onScrubGeo(long userId, long upToStatusId) {}
      public void onException(Exception ex) {}
      public void onStallWarning(StallWarning warning) {}
    };

    logger.debug("Setting up Twitter sample stream using consumer key {} and" +
          " access token {}", new String[] { consumerKey, accessToken });
    // Set up the stream's listener (defined above),
    twitterStream.addListener(listener);

    // Set up a filter to pull out industry-relevant tweets
    if (keywords.length == 0) {
      logger.debug("Starting up Twitter sampling...");
      twitterStream.sample();
    } else {
      logger.debug("Starting up Twitter filtering...");

      FilterQuery query = new FilterQuery().track(keywords);
      twitterStream.filter(query);
    }
    super.start();
  }

  /**
   * Stops the Source's event processing and shuts down the Twitter stream.
   */
  @Override
  public void stop() {
    logger.debug("Shutting down Twitter sample stream...");
    twitterStream.shutdown();
    super.stop();
  }
}
