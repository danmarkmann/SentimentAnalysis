import openai
import re
import json
import twitchio
from twitchio.ext import commands
import nltk
from nltk.sentiment import SentimentIntensityAnalyzer
nltk.download('vader_lexicon')

#pull openaikey from keyfile
with open('openaikey.txt', 'r') as f:
    openaikey = f.read()
#pull twitchkey from keyfile
with open('twitchkey.txt', 'r') as f:
    twitchkey = f.read()

# Set up OpenAI API key
openai.api_key = openaikey

def numberFromString(s):
    temp = float(''.join(ele for ele in s if ele.isdigit() or ele == '.'))
    #if temp is less than -1 or greater than 1 then it is not a valid score and return 0
    if temp < -1 or temp > 1:
        return 0
    return temp

# Define function to analyze sentiment of chat messages
def analyze_sentiment(messages):
    # Remove any newline characters and join messages into a single string
    message_text = " ".join([message.strip() for message in messages])
    #check if the message is a twitch emote in format 


    # Remove any non-alphanumeric characters (excluding spaces)
    message_text = re.sub(r'[^\w\s]', '', message_text)

    # Call OpenAI's chatgpt-3.5-turbo model to generate a response
    message_history = [{"role": "user", "content": f"Generate a sentiment score for the following message any following messages. Please use float values from 0 to 1"},
                           {"role": "assistant", "content": f"Okay I will respond with only a value from 0 to 1. 0 is the most negative and 1 is the most positive."}]
    message_history.append(
            {"role": "user", "content": f"{message_text}"})
    completion = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=message_history
        )
    print(completion.choices[0].message.content)
    #parse value from response
    tempScore = numberFromString(completion.choices[0].message.content)
    print(f"our tempscore {tempScore}")

    # Get the sentiment score from the API response
    # sentiment_score = float(completion.choices[0].message.content)

    return tempScore



########################################################
# Define function to save and load dictionary of users and their sentiment scores
def save_dict_to_json(dictionary, filename):
    with open(filename, "w") as f:
        json.dump(dictionary, f)

# Define function to save and load dictionary of users and their sentiment scores        
def load_dict_from_json(filename):
    #handle file not found error

        
    with open(filename, "r") as f:
        dictionary = json.load(f)
    return dictionary
########################################################



# Define Twitch bot class
class Bot(commands.Bot):
    # Initialise our Bot with our access token, prefix and a list of channels to join on boot...
    def __init__(self):
        super().__init__(token=twitchkey, prefix='!',
                         initial_channels=['menaceirl', 'bustin'])
    
    async def event_ready(self):
        # We are logged in and ready to chat and use commands...
        print(f'Logged in as | {self.nick}')
        print(f'User id is | {self.user_id}')

    @commands.cooldown(1, 5, bucket = commands.Bucket.channel)
    @commands.command(name='scoreGPT')
    async def scoreGPT(self, ctx):
        # normalize the score to be between 0 and 100
        #handle key error
        try:
            score = user_sentiment_scores[ctx.author.name]["avg_score"] * 100
            await ctx.send(f"{ctx.author.name} has a sentiment score of {score:.2f}.")
        except KeyError:
            await ctx.send(f"{ctx.author.name} has not sent any messages yet.")

        
    @commands.cooldown(1, 5, bucket = commands.Bucket.channel)
    @commands.command(name='vaderScore')
    async def vaderScore(self, ctx):
        # normalize the score to be between 0 and 100
        try:
            score = (user_sentiment_scores[ctx.author.name]["vaderAvg"]+1) * 50
            await ctx.send(f"{ctx.author.name} has a Vader sentiment score of {score:.2f}.")
        except KeyError:
            await ctx.send(f"{ctx.author.name} has not sent any messages yet.")

    @commands.cooldown(1, 5, bucket = commands.Bucket.channel)
    @commands.command(name='score')
    async def score(self, ctx):
        try:
            score = user_sentiment_scores[ctx.author.name]["avg_score"] * 100
            vaderScore = (user_sentiment_scores[ctx.author.name]["vaderAvg"]+1) * 50
            await ctx.send(f"{ctx.author.name} has a sentiment score of {score:.2f} and a Vader score of {vaderScore:.2f}.")
        except KeyError:
            await ctx.send(f"{ctx.author.name} has not sent any messages yet.")


class commands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot


    @commands.Cog.event()
    async def event_message(self, message):

        #start with vader sentiment analysis and return if its 0
        sid = SentimentIntensityAnalyzer()
        ss = sid.polarity_scores(message.content)
        
        
        print(f"Vader Sentiment score: {ss['compound']}")
        if ss['compound'] == 0:
            return
        # Analyze sentiment of message and update user's sentiment score
        sentiment_score = analyze_sentiment([message.content])
        print(f"openai Sentiment score: {sentiment_score}")
         # Update the user sentiment scores dictionary and handle new users
        if message.author.name not in user_sentiment_scores:
            user_sentiment_scores[message.author.name] = {"total_score": sentiment_score, "num_messages": 1, "vader_score": ss['compound']}
        else:
            user_sentiment_scores[message.author.name]["total_score"] += sentiment_score
            user_sentiment_scores[message.author.name]["num_messages"] += 1
            user_sentiment_scores[message.author.name]["vader_score"] += ss['compound']

        # Calculate the average sentiment score for each user
        for user, scores in user_sentiment_scores.items():
            avg_score = scores["total_score"] / scores["num_messages"]
            vaderAvg = scores["vader_score"] / scores["num_messages"]
            user_sentiment_scores[user]["avg_score"] = avg_score
            user_sentiment_scores[user]["vaderAvg"] = vaderAvg

        # Save the user sentiment scores dictionary to a JSON file
        save_dict_to_json(user_sentiment_scores, "user_sentiment_scores.json")



# Initialize dictionary of users and their sentiment scores
user_sentiment_scores = load_dict_from_json("user_sentiment_scores.json")

# Set up and start Twitch bot
bot = Bot()
bot.add_cog(commands(bot))
bot.run()