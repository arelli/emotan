# with lots of code from israel dryer!
import csv
from time import sleep
from msedge.selenium_tools import Edge, EdgeOptions
from selenium.webdriver.common.keys import Keys  # to simulate key presses
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait  # to wait for a page to load before accesing its elements
from selenium.webdriver.support import expected_conditions
from selenium.common import exceptions
from selenium.webdriver.common.action_chains import ActionChains  # https://stackoverflow.com/questions/61693879/python-disable-images-in-selenium-ms-edge-chromium-webdriver


import text2emotion as te  # text to emotion toolkit
import re  # regural expressions
import sys  # to execute system commands
import nltk   # natural language toolkit
nltk.download('words')  # update the natural language toolkit files


email = "---"  # your login username/phone/email
password = "---"  # your password


def create_webdriver_instance():
    options = EdgeOptions()
    options.use_chromium = True
    prefs = {"profile.managed_default_content_settings.images": 2}  # to not load images
    options.add_experimental_option("prefs", prefs)  # to not load images (faster loading?)
    driver = Edge(options=options)
    return driver


def login_to_twitter(username, password, driver):
    url = 'https://twitter.com/login'
    try:
        driver.get(url)
        xpath_username = '//input[@name="session[username_or_email]"]'
        WebDriverWait(driver, 10).until(expected_conditions.presence_of_element_located((By.XPATH, xpath_username)))
        uid_input = driver.find_element_by_xpath(xpath_username)
        uid_input.send_keys(username)
    except exceptions.TimeoutException:
        print("Timeout while waiting for Login screen")
        return False

    pwd_input = driver.find_element_by_xpath('//input[@name="session[password]"]')
    pwd_input.send_keys(password)
    try:
        pwd_input.send_keys(Keys.RETURN)
        url = "https://twitter.com/home"
        WebDriverWait(driver, 10).until(expected_conditions.url_to_be(url))
    except exceptions.TimeoutException:
        print("Timeout while waiting for home screen")
    return True


def find_search_input_and_enter_criteria(search_term, driver):
    sleep(2)
    xpath_search = '//input[@aria-label="Search query"]'
    search_input = driver.find_element_by_xpath(xpath_search)
    search_input.send_keys(search_term)
    search_input.send_keys(Keys.RETURN)
    return True


def change_page_sort(tab_name, driver):
    sleep(1)
    """Options for this program are `Latest` and `Top`"""
    tab = driver.find_element_by_link_text(tab_name)
    tab.click()
    xpath_tab_state = f'//a[contains(text(),\"{tab_name}\") and @aria-selected=\"true\"]'


def generate_tweet_id(tweet):
    return ''.join(tweet)


def scroll_down_page(driver, last_position, num_seconds_to_load=0.5, scroll_attempt=0, max_attempts=5):
    """The function will try to scroll down the page and will check the current
    and last positions as an indicator. If the current and last positions are the same after `max_attempts`
    the assumption is that the end of the scroll region has been reached and the `end_of_scroll_region`
    flag will be returned as `True`"""
    end_of_scroll_region = False
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    sleep(num_seconds_to_load)
    curr_position = driver.execute_script("return window.pageYOffset;")
    if curr_position == last_position:
        if scroll_attempt < max_attempts:
            end_of_scroll_region = True
        else:
            scroll_down_page(last_position, curr_position, scroll_attempt + 1)
    last_position = curr_position
    return last_position, end_of_scroll_region


def save_tweet_data_to_csv(records, filepath, mode='a+'):

    header = ['User', 'Handle', 'PostDate', 'TweetText', 'ReplyCount', 'RetweetCount', 'LikeCount']
    with open(filepath, mode=mode, newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        if mode == 'w':
            writer.writerow(header)
        if records:
            writer.writerow(records)


def collect_all_tweets_from_current_view(driver, lookback_limit=25):
    sleep(1)
    """The page is continously loaded, so as you scroll down the number of tweets returned by this function will
     continue to grow. To limit the risk of 're-processing' the same tweet over and over again, you can set the
     `lookback_limit` to only process the last `x` number of tweets extracted from the page in each iteration.
     You may need to play around with this number to get something that works for you. I've set the default
     based on my computer settings and internet speed, etc..."""
    page_cards = driver.find_elements_by_xpath('//div[@data-testid="tweet"]')
    if len(page_cards) <= lookback_limit:
        return page_cards
    else:
        return page_cards[-lookback_limit:]

words = set(nltk.corpus.words.words())  #to let only english words in the text
def extract_data_from_current_tweet_card(card):
    try:
        user = card.find_element_by_xpath('.//span').text
    except exceptions.NoSuchElementException:
        user = ""
    except exceptions.StaleElementReferenceException:
        return
    try:
        handle = card.find_element_by_xpath('.//span[contains(text(), "@")]').text
    except exceptions.NoSuchElementException:
        handle = ""
    try:
        """
        If there is no post date here, there it is usually sponsored content, or some
        other form of content where post dates do not apply. You can set a default value
        for the postdate on Exception if you which to keep this record. By default I am
        excluding these.
        """
        postdate = card.find_element_by_xpath('.//time').get_attribute('datetime')
    except exceptions.NoSuchElementException:
        return
    try:
        _comment = card.find_element_by_xpath('.//div[2]/div[2]/div[1]').text
    except exceptions.NoSuchElementException:
        _comment = "0"
    try:
        _responding = card.find_element_by_xpath('.//div[2]/div[2]/div[2]').text
    except exceptions.NoSuchElementException:
        _responding = "0"
    tweet_text = _comment + _responding
    try:
        reply_count = card.find_element_by_xpath('.//div[@data-testid="reply"]').text
    except exceptions.NoSuchElementException:
        reply_count = "0"
    try:
        retweet_count = card.find_element_by_xpath('.//div[@data-testid="retweet"]').text
    except exceptions.NoSuchElementException:
        retweet_count = "0"
    try:
        like_count = card.find_element_by_xpath('.//div[@data-testid="like"]').text
    except exceptions.NoSuchElementException:
        like_count = "0"

    x = tweet_text
    x = tweet_text
    x = ''.join([i for i in x if not i.isdigit()])
    x = ' '.join(re.sub("(@[A-Za-z0-9]+)|([^0-9A-Za-z \t])|(\w+:\/\/\S+)", " ", x).split())  # clean the tweet
    x = " ".join(w for w in nltk.wordpunct_tokenize(x) \
                 if w.lower() in words or not w.isalpha())
    x = ' '.join([w for w in x.split() if len(w) > 1])  # remove single letter words
    tweet_text = x

    tweet = (user, handle, postdate, tweet_text, reply_count, retweet_count, like_count)
    return tweet



def main(username, password, search_term, filepath, page_sort='Latest'):
    total_happiness = 0
    total_angryness = 0
    total_suprsiseness = 0
    total_saddness = 0
    total_fearness = 0
    number_of_tweets = 1

    save_tweet_data_to_csv(None, filepath, 'w')  # create file for saving records
    last_position = None
    end_of_scroll_region = False
    unique_tweets = set()

    driver = create_webdriver_instance()
    logged_in = login_to_twitter(username, password, driver)
    if not logged_in:
        return

    search_found = find_search_input_and_enter_criteria(search_term, driver)
    if not search_found:
        return

    change_page_sort(page_sort, driver)


    while not end_of_scroll_region:
        cards = collect_all_tweets_from_current_view(driver)
        for card in cards:
            try:
                tweet = extract_data_from_current_tweet_card(card)
            except exceptions.StaleElementReferenceException:
                continue
            if not tweet:
                continue
            tweet_id = generate_tweet_id(tweet)
            if tweet_id not in unique_tweets:
                unique_tweets.add(tweet_id)
                save_tweet_data_to_csv(tweet, filepath)
                tweet_str = str(tweet)
                tweet_text = tweet_str.split(",")[3]
                tweet_emotion = te.get_emotion(tweet_text)
                print("\n\n\n\n\n\n\n\n\n\n\n\n\n")
                print( "Tweet no." + str(number_of_tweets)+ " text:" + str(tweet_text)[0:100] + "...")
                total_happiness += float(tweet_emotion["Happy"]) /number_of_tweets
                total_angryness += float(tweet_emotion["Angry"]) /number_of_tweets
                total_suprsiseness += float(tweet_emotion["Surprise"]) /number_of_tweets
                total_saddness += float(tweet_emotion["Sad"]) /number_of_tweets
                total_fearness += float(tweet_emotion["Fear"]) /number_of_tweets
                print("happiness:" + str(total_happiness) + "," + "angry:" + str(total_angryness) + "," + "surprise:" + str(total_suprsiseness) + "," + "sad:" + str(total_saddness) + "," + "fearness:" + str(total_fearness))
                number_of_tweets += 1

        last_position, end_of_scroll_region = scroll_down_page(driver, last_position)
    driver.quit()


if __name__ == '__main__':
    usr = email
    pwd = password
    term = 'police brutality'
    path = term + '.csv'

    main(usr, pwd, term, path)
