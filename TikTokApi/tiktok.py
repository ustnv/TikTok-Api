import json
import logging
import os
import random
import string
import re
import time
from urllib.parse import quote, urlencode
import datetime
import requests
from playwright.sync_api import sync_playwright

from .exceptions import *
from .utilities import update_messager


os.environ["no_proxy"] = "127.0.0.1,localhost"

BASE_URL = "https://m.tiktok.com/"


class TikTokApi:
    __instance = None

    def __init__(self, **kwargs):
        """The TikTokApi class. Used to interact with TikTok, use get_instance NOT this."""
        # Forces Singleton
        if TikTokApi.__instance is None:
            TikTokApi.__instance = self
        else:
            raise Exception("Only one TikTokApi object is allowed")
        logging.basicConfig(level=kwargs.get("logging_level", logging.WARNING))
        logging.info("Class initalized")

        # Some Instance Vars
        self.executablePath = kwargs.get("executablePath", None)

        if kwargs.get("custom_did") != None:
            raise Exception("Please use custom_device_id instead of custom_device_id")
        self.custom_device_id = kwargs.get("custom_device_id", None)
        self.userAgent = (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/86.0.4240.111 Safari/537.36"
        )
        self.proxy = kwargs.get("proxy", None)
        self.custom_verifyFp = kwargs.get("custom_verifyFp")
        self.signer_url = kwargs.get("external_signer", None)
        self.request_delay = kwargs.get("request_delay", None)
        self.requests_extra_kwargs = kwargs.get("requests_extra_kwargs", {})

        if kwargs.get("use_test_endpoints", False):
            global BASE_URL
            BASE_URL = "https://t.tiktok.com/"
        if kwargs.get("use_selenium", False):
            from .browser_utilities.browser_selenium import browser
        else:
            from .browser_utilities.browser import browser

        if kwargs.get("generate_static_device_id", False):
            self.custom_device_id = "".join(random.choice(string.digits) for num in range(19))

        if self.signer_url is None:
            self.browser = browser(**kwargs)
            self.userAgent = self.browser.userAgent

        try:
            self.timezone_name = self.__format_new_params__(self.browser.timezone_name)
            self.browser_language = self.__format_new_params__(
                self.browser.browser_language
            )
            self.width = self.browser.width
            self.height = self.browser.height
            self.region = self.browser.region
            self.language = self.browser.language
        except Exception as e:
            logging.exception(e)
            logging.warning("An error ocurred while opening your browser but it was ignored.")
            logging.warning("Are you sure you ran python -m playwright install")

            self.timezone_name = ""
            self.browser_language = ""
            self.width = "1920"
            self.height = "1080"
            self.region = "US"
            self.language = "en"

    @staticmethod
    def get_instance(**kwargs):
        """The TikTokApi class. Used to interact with TikTok. This is a singleton
            class to prevent issues from arising with playwright

        ##### Parameters
        * logging_level: The logging level you want the program to run at, optional
            These are the standard python logging module's levels.

        * request_delay: The amount of time to wait before making a request, optional
            This is used to throttle your own requests as you may end up making too
            many requests to TikTok for your IP.

        * custom_device_id: A TikTok parameter needed to download videos, optional
            The code generates these and handles these pretty well itself, however
            for some things such as video download you will need to set a consistent
            one of these. All the methods take this as a optional parameter, however
            it's cleaner code to store this at the instance level. You can override
            this at the specific methods.

        * generate_static_device_id: A parameter that generates a custom_device_id at the instance level
            Use this if you want to download videos from a script but don't want to generate
            your own custom_device_id parameter.

        * custom_verifyFp: A TikTok parameter needed to work most of the time, optional
            To get this parameter look at [this video](https://youtu.be/zwLmLfVI-VQ?t=117)
            I recommend watching the entire thing, as it will help setup this package. All
            the methods take this as a optional parameter, however it's cleaner code
            to store this at the instance level. You can override this at the specific
            methods.

            You can use the following to generate `"".join(random.choice(string.digits)
            for num in range(19))`

        * use_test_endpoints: Send requests to TikTok's test endpoints, optional
            This parameter when set to true will make requests to TikTok's testing
            endpoints instead of the live site. I can't guarantee this will work
            in the future, however currently basically any custom_verifyFp will
            work here which is helpful.

        * proxy: A string containing your proxy address, optional
            If you want to do a lot of scraping of TikTok endpoints you'll likely
            need a proxy.

            Ex: "https://0.0.0.0:8080"

            All the methods take this as a optional parameter, however it's cleaner code
            to store this at the instance level. You can override this at the specific
            methods.

        * use_selenium: Option to use selenium over playwright, optional
            Playwright is selected by default and is the one that I'm designing the
            package to be compatable for, however if playwright doesn't work on
            your machine feel free to set this to True.

        * executablePath: The location of the driver, optional
            This shouldn't be needed if you're using playwright

        * **kwargs
            Parameters that are passed on to basically every module and methods
            that interact with this main class. These may or may not be documented
            in other places.
        """
        if not TikTokApi.__instance:
            TikTokApi(**kwargs)
        return TikTokApi.__instance

    def clean_up(self):
        """A basic cleanup method, called automatically from the code"""
        self.__del__()

    def __del__(self):
        """A basic cleanup method, called automatically from the code"""
        try:
            self.browser.clean_up()
        except Exception:
            pass
        try:
            get_playwright().stop()
        except Exception:
            pass
        TikTokApi.__instance = None

    def external_signer(self, url, custom_device_id=None, verifyFp=None):
        """Makes requests to an external signer instead of using a browser.

        ##### Parameters
        * url: The server to make requests to
            This server is designed to sign requests. You can find an example
            of this signature server in the examples folder.

        * custom_device_id: A TikTok parameter needed to download videos
            The code generates these and handles these pretty well itself, however
            for some things such as video download you will need to set a consistent
            one of these.

        * custom_verifyFp: A TikTok parameter needed to work most of the time,
            To get this parameter look at [this video](https://youtu.be/zwLmLfVI-VQ?t=117)
            I recommend watching the entire thing, as it will help setup this package.
        """
        if custom_device_id is not None:
            query = {"url": url, "custom_device_id": custom_device_id, "verifyFp": verifyFp}
        else:
            query = {"url": url, "verifyFp": verifyFp}

        try:
            data = requests.request("POST", self.signer_url, data=url, timeout=10)
        except:
            time.sleep(10)
            data = requests.request("POST", self.signer_url, data=url, timeout=60)

        parsed_data = data.json()['data']

        return (
            parsed_data.get("verify_fp"),
            parsed_data.get("device_id"),  # device_id
            parsed_data.get("signature"),
            parsed_data.get("navigator").get("user_agent"),
            parsed_data.get("referrer"),
            parsed_data.get("x-tt-params")
        )

    def get_data(self, **kwargs) -> dict:
        """Makes requests to TikTok and returns their JSON.

        This is all handled by the package so it's unlikely
        you will need to use this.
        """
        (
            region,
            language,
            proxy,
            maxCount,
            device_id,
        ) = self.__process_kwargs__(kwargs)
        kwargs["custom_device_id"] = device_id
        if self.request_delay is not None:
            time.sleep(self.request_delay)

        if self.proxy is not None:
            proxy = self.proxy

        if kwargs.get("custom_verifyFp") == None:
            if self.custom_verifyFp != None:
                verifyFp = self.custom_verifyFp
            else:
                verifyFp = "verify_khr3jabg_V7ucdslq_Vrw9_4KPb_AJ1b_Ks706M8zIJTq"
        else:
            verifyFp = kwargs.get("custom_verifyFp")

        tt_params = None
        send_tt_params = kwargs.get("send_tt_params", False)

        if self.signer_url is None:
            kwargs["custom_verifyFp"] = verifyFp
            verify_fp, device_id, signature, tt_params = self.browser.sign_url(calc_tt_params=send_tt_params, **kwargs)
            userAgent = self.browser.userAgent
            referrer = self.browser.referrer
        else:
            verify_fp, device_id, signature, userAgent, referrer, tt_params = self.external_signer(
                kwargs["url"],
                custom_device_id=kwargs.get("custom_device_id"),
                verifyFp=kwargs.get("custom_verifyFp", verifyFp),
            )

        if not kwargs.get("send_tt_params", False):
            tt_params = None

        query = {"verifyFp": verify_fp, "_signature": signature}
        url = "{}&{}".format(kwargs["url"], urlencode(query))

        done = False
        n = 1
        while not done:
            try:

                h = requests.head(
                    url,
                    headers={"x-secsdk-csrf-version": "1.2.5", "x-secsdk-csrf-request": "1"},
                    proxies=self.__format_proxy(proxy),
                    timeout=5,
                    **self.requests_extra_kwargs,
                )
                csrf_session_id = h.cookies["csrf_session_id"]
                csrf_token = h.headers["X-Ware-Csrf-Token"].split(",")[1]
                kwargs["csrf_session_id"] = csrf_session_id

                r = requests.get(
                    url,
                    headers={
                        "authority": "m.tiktok.com",
                        "method": "GET",
                        "path": url.split("tiktok.com")[1],
                        "scheme": "https",
                        "accept": "application/json, text/plain, */*",
                        "accept-encoding": "gzip, deflate, br",
                        "accept-language": "en-US,en;q=0.9",
                        "origin": referrer,
                        "referer": referrer,
                        "sec-fetch-dest": "empty",
                        "sec-fetch-mode": "cors",
                        "sec-fetch-site": "same-site",
                        "sec-gpc": "1",
                        "user-agent": userAgent,
                        "x-secsdk-csrf-token": csrf_token,
                        "x-tt-params": tt_params
                    },
                    cookies=self.get_cookies(**kwargs),
                    proxies=self.__format_proxy(proxy),
                    timeout=5,
                    **self.requests_extra_kwargs,
                )
            except Exception as e:
                r = None
                if not (n % 10):
                    logging.error('retry ' + str(n))
                    logging.error(e.__class__.__name__)
                n = n + 1
                time.sleep(2)

                if n > 100:
                    done = True

            if r:
                try:
                    json = r.json()
                    if (
                            json.get("type") == "verify"
                            or json.get("verifyConfig", {}).get("type", "") == "verify"
                    ):
                        logging.error(
                            "Tiktok wants to display a catcha."
                        )
                        # logging.error(self.get_cookies(**kwargs))
                        time.sleep(2)
                        # raise TikTokCaptchaError()
                    elif json.get("statusCode", 200) == 10201:
                        # Invalid Entity
                        raise TikTokNotFoundError(
                            "TikTok returned a response indicating the entity is invalid"
                        )
                    elif json.get("statusCode", 200) == 10219:
                        # not available in this region
                        raise TikTokNotAvailableError(
                            "Content not available for this region"
                        )
                    else:
                        return r.json()
                except ValueError as e:
                    text = r.text
                    logging.error("TikTok response: " + text)
                    time.sleep(2)

    def get_cookies(self, **kwargs):
        """Extracts cookies from the kwargs passed to the function for get_data"""
        device_id = kwargs.get(
            "custom_device_id", "".join(random.choice(string.digits) for num in range(19))
        )
        if kwargs.get("custom_verifyFp") == None:
            if self.custom_verifyFp != None:
                verifyFp = self.custom_verifyFp
            else:
                verifyFp = "verify_khr3jabg_V7ucdslq_Vrw9_4KPb_AJ1b_Ks706M8zIJTq"
        else:
            verifyFp = kwargs.get("custom_verifyFp")

        if kwargs.get("force_verify_fp_on_cookie_header", False):
            return {
                "tt_webid": device_id,
                "tt_webid_v2": device_id,
                "csrf_session_id": kwargs.get("csrf_session_id"),
                "tt_csrf_token": "".join(
                    random.choice(string.ascii_uppercase + string.ascii_lowercase)
                    for i in range(16)
                ),
                "s_v_web_id": verifyFp,
            }
        else:
            return {
                "tt_webid": device_id,
                "tt_webid_v2": device_id,
                "csrf_session_id": kwargs.get("csrf_session_id"),
                "tt_csrf_token": "".join(
                    random.choice(string.ascii_uppercase + string.ascii_lowercase)
                    for i in range(16)
                ),
            }

    def get_bytes(self, **kwargs) -> bytes:
        """Returns TikTok's response as bytes, similar to get_data"""
        (
            region,
            language,
            proxy,
            maxCount,
            device_id,
        ) = self.__process_kwargs__(kwargs)
        kwargs["custom_device_id"] = device_id
        if self.signer_url is None:
            verify_fp, device_id, signature, _ = self.browser.sign_url(calc_tt_params=False, **kwargs)
            userAgent = self.browser.userAgent
            referrer = self.browser.referrer
        else:
            verify_fp, device_id, signature, userAgent, referrer = self.external_signer(
                kwargs["url"], custom_device_id=kwargs.get("custom_device_id", None)
            )
        query = {"verifyFp": verify_fp, "_signature": signature}
        url = "{}&{}".format(kwargs["url"], urlencode(query))
        r = requests.get(
            url,
            headers={
                "Accept": "*/*",
                "Accept-Encoding": "identity;q=1, *;q=0",
                "Accept-Language": "en-US;en;q=0.9",
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Host": url.split("/")[2],
                "Pragma": "no-cache",
                "Range": "bytes=0-",
                "Referer": "https://www.tiktok.com/",
                "User-Agent": userAgent,
            },
            proxies=self.__format_proxy(proxy),
            cookies=self.get_cookies(**kwargs),
        )
        return r.content

    def by_trending(self, count=30, **kwargs) -> dict:
        """
        Gets trending TikToks

        ##### Parameters
        * count: The amount of TikToks you want returned, optional

            Note: TikTok seems to only support at MOST ~2000 TikToks
            from a single endpoint.
        """
        (
            region,
            language,
            proxy,
            maxCount,
            device_id,
        ) = self.__process_kwargs__(kwargs)
        kwargs["custom_device_id"] = device_id

        response = []
        first = True

        while len(response) < count:
            if count < maxCount:
                realCount = count
            else:
                realCount = maxCount

            query = {
                "count": realCount,
                "id": 1,
                "secUid": "",
                "sourceType": 12,
                "appId": 1233,
                "itemID": 1,
                "insertedItemID": "",
                "region": region,
                "priority_region": region,
                "language": language,
            }
            api_url = "{}api/recommend/item_list/?{}&{}".format(
                BASE_URL, self.__add_url_params__(), urlencode(query)
            )
            res = self.get_data(url=api_url, **kwargs)
            for t in res.get("itemList", []):
                response.append(t)

            if not res.get("hasMore", False) and not first:
                logging.info("TikTok isn't sending more TikToks beyond this point.")
                return response[:count]

            realCount = count - len(response)

            first = False

        return response[:count]

    def search_for_users(self, search_term, count=28, **kwargs) -> list:
        """Returns a list of users that match the search_term

        ##### Parameters
        * search_term: The string to search for users by
            This string is the term you want to search for users by.

        * count: The number of users to return
            Note: maximum is around 28 for this type of endpoint.
        """
        return self.discover_type(search_term, prefix="user", count=count, **kwargs)

    def search_for_music(self, search_term, count=28, **kwargs) -> list:
        """Returns a list of music that match the search_term

        ##### Parameters
        * search_term: The string to search for music by
            This string is the term you want to search for music by.

        * count: The number of music to return
            Note: maximum is around 28 for this type of endpoint.
        """
        return self.discover_type(search_term, prefix="music", count=count, **kwargs)

    def search_for_hashtags(self, search_term, count=28, **kwargs) -> list:
        """Returns a list of hashtags that match the search_term

        ##### Parameters
        * search_term: The string to search for music by
            This string is the term you want to search for music by.

        * count: The number of music to return
            Note: maximum is around 28 for this type of endpoint.
        """
        return self.discover_type(
            search_term, prefix="challenge", count=count, **kwargs
        )

    def discover_type(self, search_term, prefix, count=28, offset=0, **kwargs) -> list:
        """Returns a list of whatever the prefix type you pass in

        ##### Parameters
        * search_term: The string to search by

        * prefix: The prefix of what to search for

        * count: The number search results to return
            Note: maximum is around 28 for this type of endpoint.
        """
        (
            region,
            language,
            proxy,
            maxCount,
            device_id,
        ) = self.__process_kwargs__(kwargs)
        kwargs["custom_device_id"] = device_id

        response = []
        while len(response) < count:
            query = {
                "discoverType": 1,
                "needItemList": False,
                "keyWord": search_term,
                "offset": offset,
                "count": count,
                "useRecommend": False,
                "language": "en",
            }
            api_url = "{}api/discover/{}/?{}&{}".format(
                BASE_URL, prefix, self.__add_url_params__(), urlencode(query)
            )
            data = self.get_data(url=api_url, **kwargs)

            if "userInfoList" in data.keys():
                for x in data["userInfoList"]:
                    response.append(x)
            elif "musicInfoList" in data.keys():
                for x in data["musicInfoList"]:
                    response.append(x)
            elif "challengeInfoList" in data.keys():
                for x in data["challengeInfoList"]:
                    response.append(x)
            else:
                logging.info("TikTok is not sending videos beyond this point.")
                break

            offset += maxCount

        return response[:count]

    def user_posts(self, userID, secUID, count=30, cursor=0, **kwargs) -> dict:
        """Returns an array of dictionaries representing TikToks for a user.

        ##### Parameters
        * userID: The userID of the user, which TikTok assigns

            You can find this from utilizing other methods or
            just use by_username to find it.
        * secUID: The secUID of the user, which TikTok assigns

            You can find this from utilizing other methods or
            just use by_username to find it.
        * count: The number of posts to return

            Note: seems to only support up to ~2,000
        """
        (
            region,
            language,
            proxy,
            maxCount,
            device_id,
        ) = self.__process_kwargs__(kwargs)
        kwargs["custom_device_id"] = device_id

        response = []
        first = True

        last_time = int((datetime.datetime.now() + datetime.timedelta(days=1)).strftime('%s'))
        if not kwargs.get('time_limit'):
            time_limit = int((datetime.datetime.now()).strftime('%s'))
        else:
            time_limit = kwargs.get('time_limit')

        while last_time > time_limit:
            if count < maxCount:
                realCount = count
            else:
                realCount = maxCount

            query = {
                "count": realCount,
                "id": userID,
                "cursor": cursor,
                "type": 1,
                "secUid": secUID,
                "sourceType": 8,
                "appId": 1233,
                "region": region,
                "priority_region": region,
                "language": language,
            }
            api_url = "{}api/post/item_list/?{}&{}".format(
                BASE_URL, self.__add_url_params__(), urlencode(query)
            )

            res = self.get_data(url=api_url, send_tt_params=True, **kwargs)

            if res is None:
                logging.info("Result is None.")
                return []

            if "itemList" in res.keys():
                for t in res.get("itemList", []):
                    response.append(t)

            if (not "itemList" in res.keys() or not res.get("hasMore")) and not first:
                logging.info("TikTok isn't sending more TikToks beyond this point.")
                return response

            realCount = count - len(response)
            cursor = res["cursor"]
            if response:
                last_time = response[-1].get('createTime')

            first = False

        return response[:count]

    def by_username(self, username, count=30, **kwargs) -> dict:
        """Returns a dictionary listing TikToks given a user's username.

        ##### Parameters
        * username: The username of the TikTok user to get TikToks from

        * count: The number of posts to return

            Note: seems to only support up to ~2,000
        """
        (
            region,
            language,
            proxy,
            maxCount,
            device_id,
        ) = self.__process_kwargs__(kwargs)
        kwargs["custom_device_id"] = device_id
        data = self.get_user_object(username, **kwargs)
        return self.user_posts(
            data["id"],
            data["secUid"],
            count=count,
            **kwargs,
        )

    def user_page(self, userID, secUID, page_size=30, cursor=0, **kwargs) -> dict:
        """Returns a dictionary listing of one page of TikToks given a user's ID and secUID

        ##### Parameters
        * userID: The userID of the user, which TikTok assigns

            You can find this from utilizing other methods or
            just use by_username to find it.
        * secUID: The secUID of the user, which TikTok assigns

            You can find this from utilizing other methods or
            just use by_username to find it.
        * page_size: The number of posts to return per page

            Gets a specific page of a user, doesn't iterate.
        * cursor: The offset of a page

            The offset to return new videos from
        """
        (
            region,
            language,
            proxy,
            maxCount,
            device_id,
        ) = self.__process_kwargs__(kwargs)
        kwargs["custom_device_id"] = device_id

        api_url = (
            BASE_URL + "api/post/item_list/?{}&count={}&id={}&type=1&secUid={}"
            "&cursor={}&sourceType=8&appId=1233&region={}&language={}".format(
                self.__add_url_params__(),
                page_size,
                str(userID),
                str(secUID),
                cursor,
                region,
                language,
            )
        )

        return self.get_data(url=api_url, send_tt_params=True, **kwargs)

    def get_user_pager(self, username, page_size=30, cursor=0, **kwargs):
        """Returns a generator to page through a user's feed

        ##### Parameters
        * username: The username of the user

        * page_size: The number of posts to return in a page

        * cursor: The offset of a page

            The offset to return new videos from
        """
        (
            region,
            language,
            proxy,
            maxCount,
            device_id,
        ) = self.__process_kwargs__(kwargs)
        kwargs["custom_device_id"] = device_id
        data = self.get_user_object(username, **kwargs)

        while True:
            resp = self.user_page(
                data["id"],
                data["secUid"],
                page_size=page_size,
                cursor=cursor,
                **kwargs,
            )

            try:
                page = resp["itemList"]
            except KeyError:
                # No mo results
                return

            cursor = resp["cursor"]

            yield page

            if not resp["hasMore"]:
                return  # all done

    def user_liked(self, userID, secUID, count=30, cursor=0, **kwargs) -> dict:
        """Returns a dictionary listing TikToks that a given a user has liked.
            Note: The user's likes must be public

        ##### Parameters
        * userID: The userID of the user, which TikTok assigns

        * secUID: The secUID of the user, which TikTok assigns

        * count: The number of posts to return

            Note: seems to only support up to ~2,000
        * cursor: The offset of a page

            The offset to return new videos from
        """
        (
            region,
            language,
            proxy,
            maxCount,
            device_id,
        ) = self.__process_kwargs__(kwargs)
        kwargs["custom_device_id"] = device_id
        response = []
        first = True

        while len(response) < count:
            if count < maxCount:
                realCount = count
            else:
                realCount = maxCount

            query = {
                "count": realCount,
                "id": userID,
                "type": 2,
                "secUid": secUID,
                "cursor": cursor,
                "sourceType": 9,
                "appId": 1233,
                "region": region,
                "priority_region": region,
                "language": language,
            }
            api_url = "{}api/favorite/item_list/?{}&{}".format(
                BASE_URL, self.__add_url_params__(), urlencode(query)
            )

            res = self.get_data(url=api_url, **kwargs)

            try:
                res["itemList"]
            except Exception:
                logging.error("User's likes are most likely private")
                return []

            for t in res.get("itemList", []):
                response.append(t)

            if not res.get("hasMore", False) and not first:
                logging.info("TikTok isn't sending more TikToks beyond this point.")
                return response

            realCount = count - len(response)
            cursor = res["cursor"]

            first = False

        return response[:count]

    def user_liked_by_username(self, username, count=30, **kwargs) -> dict:
        """Returns a dictionary listing TikToks a user has liked by username.
            Note: The user's likes must be public

        ##### Parameters
        * username: The username of the user

        * count: The number of posts to return

            Note: seems to only support up to ~2,000
        """
        (
            region,
            language,
            proxy,
            maxCount,
            device_id,
        ) = self.__process_kwargs__(kwargs)
        kwargs["custom_device_id"] = device_id
        data = self.get_user_object(username, **kwargs)
        return self.user_liked(
            data["id"],
            data["secUid"],
            count=count,
            **kwargs,
        )

    def by_sound(self, id, count=30, offset=0, **kwargs) -> dict:
        """Returns a dictionary listing TikToks with a specific sound.

        ##### Parameters
        * id: The sound id to search by

            Note: Can be found in the URL of the sound specific page or with other methods.
        * count: The number of posts to return

            Note: seems to only support up to ~2,000
        """
        (
            region,
            language,
            proxy,
            maxCount,
            device_id,
        ) = self.__process_kwargs__(kwargs)
        kwargs["custom_device_id"] = device_id
        response = []

        while len(response) < count:
            if count < maxCount:
                realCount = count
            else:
                realCount = maxCount

            query = {
                "secUid": "",
                "musicID": str(id),
                "count": str(realCount),
                "cursor": offset,
                "shareUid": "",
                "language": language,
            }
            api_url = "{}api/music/item_list/?{}&{}".format(
                BASE_URL, self.__add_url_params__(), urlencode(query)
            )

            res = self.get_data(url=api_url, send_tt_params=True, **kwargs)

            try:
                for t in res["items"]:
                    response.append(t)
            except KeyError:
                for t in res.get("itemList", []):
                    response.append(t)

            if not res.get("hasMore", False):
                logging.info("TikTok isn't sending more TikToks beyond this point.")
                return response

            realCount = count - len(response)
            offset = res["cursor"]

        return response[:count]


    def by_sound_page(self, id, page_size=30, cursor=0, **kwargs) -> dict:
        """Returns a page of tiktoks with a specific sound.

        Parameters
        ----------
        id: The sound id to search by
            Note: Can be found in the URL of the sound specific page or with other methods.
        cursor: offset for pagination
        page_size: The number of posts to return
        """
        (
            region,
            language,
            proxy,
            maxCount,
            device_id,
        ) = self.__process_kwargs__(kwargs)
        kwargs["custom_device_id"] = device_id

        query = {
            "musicID": str(id),
            "count": str(page_size),
            "cursor": cursor,
            "language": language,
        }
        api_url = "{}api/music/item_list/?{}&{}".format(
            BASE_URL, self.__add_url_params__(), urlencode(query)
        )

        return self.get_data(url=api_url, send_tt_params=True, **kwargs)


    def get_music_object(self, id, **kwargs) -> dict:
        """Returns a music object for a specific sound id.

        ##### Parameters
        * id: The sound id to get the object for

            This can be found by using other methods.
        """
        return self.get_music_object_full(id, **kwargs)["music"]

    def get_music_object_full(self, id, **kwargs):
        """Returns a music object for a specific sound id.

        ##### Parameters
        * id: The sound id to get the object for

            This can be found by using other methods.
        """
        (
            region,
            language,
            proxy,
            maxCount,
            device_id,
        ) = self.__process_kwargs__(kwargs)
        r = requests.get(
            "https://www.tiktok.com/music/-{}".format(id),
            headers={
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
                "authority": "www.tiktok.com",
                "Accept-Encoding": "gzip, deflate",
                "Connection": "keep-alive",
                "Host": "www.tiktok.com",
                "User-Agent": self.userAgent,
            },
            proxies=self.__format_proxy(kwargs.get("proxy", None)),
            cookies=self.get_cookies(**kwargs),
            **self.requests_extra_kwargs,
        )

        j_raw = self.__extract_tag_contents(r.text)
        return json.loads(j_raw)["props"]["pageProps"]["musicInfo"]

    def get_music_object_full_by_api(self, id, **kwargs):
        """Returns a music object for a specific sound id, but using the API rather than HTML requests.

        ##### Parameters
        * id: The sound id to get the object for

            This can be found by using other methods.
        """
        (
            region,
            language,
            proxy,
            maxCount,
            device_id,
        ) = self.__process_kwargs__(kwargs)
        kwargs["custom_device_id"] = device_id

        api_url = "{}node/share/music/-{}?{}".format(
            BASE_URL, id, self.__add_url_params__()
        )
        res = self.get_data(url=api_url, **kwargs)

        if res.get("statusCode", 200) == 10203:
            raise TikTokNotFoundError()

        return res["musicInfo"]

    def by_hashtag(self, hashtag, count=30, offset=0, **kwargs) -> dict:
        """Returns a dictionary listing TikToks with a specific hashtag.

        ##### Parameters
        * hashtag: The hashtag to search by

            Without the # symbol

            A valid string is "funny"
        * count: The number of posts to return
            Note: seems to only support up to ~2,000
        """
        (
            region,
            language,
            proxy,
            maxCount,
            device_id,
        ) = self.__process_kwargs__(kwargs)
        kwargs["custom_device_id"] = device_id
        id = self.get_hashtag_object(hashtag)["challengeInfo"]["challenge"]["id"]
        response = []

        required_count = count

        while len(response) < required_count:
            if count > maxCount:
                count = maxCount
            query = {
                "count": count,
                "challengeID": id,
                "type": 3,
                "secUid": "",
                "cursor": offset,
                "priority_region": "",
            }
            api_url = "{}api/challenge/item_list/?{}&{}".format(
                BASE_URL, self.__add_url_params__(), urlencode(query)
            )
            res = self.get_data(url=api_url, **kwargs)

            for t in res.get("itemList", []):
                response.append(t)

            if not res.get("hasMore", False):
                logging.info("TikTok isn't sending more TikToks beyond this point.")
                return response

            offset += maxCount

        return response[:required_count]

    def get_hashtag_object(self, hashtag, **kwargs) -> dict:
        """Returns a hashtag object.

        ##### Parameters
        * hashtag: The hashtag to search by

            Without the # symbol
        """
        (
            region,
            language,
            proxy,
            maxCount,
            device_id,
        ) = self.__process_kwargs__(kwargs)
        kwargs["custom_device_id"] = device_id
        query = {"name": hashtag, "isName": True, "lang": language}
        api_url = "{}node/share/tag/{}?{}&{}".format(
            BASE_URL, quote(hashtag), self.__add_url_params__(), urlencode(query)
        )
        data = self.get_data(url=api_url, **kwargs)
        if data["challengeInfo"].get("challenge") is None:
            raise TikTokNotFoundError("Challenge {} does not exist".format(hashtag))
        return data

    def get_recommended_tiktoks_by_video_id(self, id, count=30, **kwargs) -> dict:
        """Returns a dictionary listing reccomended TikToks for a specific TikTok video.


        ##### Parameters
        * id: The id of the video to get suggestions for

            Can be found using other methods
        * count: The count of results you want to return
        """
        (
            region,
            language,
            proxy,
            maxCount,
            device_id,
        ) = self.__process_kwargs__(kwargs)
        kwargs["custom_device_id"] = device_id

        response = []
        first = True

        while len(response) < count:
            if count < maxCount:
                realCount = count
            else:
                realCount = maxCount

            query = {
                "count": realCount,
                "id": 1,
                "secUid": "",
                "sourceType": 12,
                "appId": 1233,
                "region": region,
                "priority_region": region,
                "language": language,
            }
            api_url = "{}api/recommend/item_list/?{}&{}".format(
                BASE_URL, self.__add_url_params__(), urlencode(query)
            )

            res = self.get_data(url=api_url, **kwargs)

            for t in res.get("itemList", []):
                response.append(t)

            if not res.get("hasMore", False) and not first:
                logging.info("TikTok isn't sending more TikToks beyond this point.")
                return response[:count]

            realCount = count - len(response)

            first = False

        return response[:count]

    def get_tiktok_by_id(self, id, **kwargs) -> dict:
        """Returns a dictionary of a specific TikTok.

        ##### Parameters
        * id: The id of the TikTok you want to get the object for
        """
        (
            region,
            language,
            proxy,
            maxCount,
            device_id,
        ) = self.__process_kwargs__(kwargs)
        kwargs["custom_device_id"] = device_id
        device_id = kwargs.get("custom_device_id", None)
        query = {
            "itemId": id,
            "language": language,
        }
        api_url = "{}api/item/detail/?{}&{}".format(
            BASE_URL, self.__add_url_params__(), urlencode(query)
        )

        return self.get_data(url=api_url, **kwargs)

    def get_tiktok_by_url(self, url, **kwargs) -> dict:
        """Returns a dictionary of a TikTok object by url.


        ##### Parameters
        * url: The TikTok url you want to retrieve

            This currently doesn't support the shortened TikTok
            url links.
        """
        (
            region,
            language,
            proxy,
            maxCount,
            device_id,
        ) = self.__process_kwargs__(kwargs)
        kwargs["custom_device_id"] = device_id
        custom_device_id = kwargs.get("custom_device_id", None)
        if "@" in url and "/video/" in url:
            post_id = url.split("/video/")[1].split("?")[0]
        else:
            raise Exception(
                "URL format not supported. Below is an example of a supported url.\n"
                "https://www.tiktok.com/@therock/video/6829267836783971589"
            )

        return self.get_tiktok_by_id(
            post_id,
            **kwargs,
        )

    def get_tiktok_by_html(self, url, **kwargs) -> dict:
        """This method retrieves a TikTok using the html
        endpoints rather than the API based ones.

        ##### Parameters
        * url: The url of the TikTok to get
        """
        (
            region,
            language,
            proxy,
            maxCount,
            device_id,
        ) = self.__process_kwargs__(kwargs)

        r = requests.get(
            url,
            headers={
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
                "authority": "www.tiktok.com",
                "path": url.split("tiktok.com")[1],
                "Accept-Encoding": "gzip, deflate",
                "Connection": "keep-alive",
                "Host": "www.tiktok.com",
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/86.0.4240.111 Safari/537.36",
            },
            proxies=self.__format_proxy(kwargs.get("proxy", None)),
            cookies=self.get_cookies(**kwargs),
            **self.requests_extra_kwargs,
        )

        t = r.text
        try:
            j_raw = self.__extract_tag_contents(r.text)
        except IndexError:
            if not t:
                logging.error("TikTok response is empty")
            else:
                logging.error("TikTok response: \n " + t)
            raise TikTokCaptchaError()

        data = json.loads(j_raw)["props"]["pageProps"]

        if data["serverCode"] == 404:
            raise TikTokNotFoundError("TikTok with that url doesn't exist")

        return data

    def discover_hashtags(self, **kwargs) -> dict:
        """Discover page, consists challenges (hashtags)"""
        (
            region,
            language,
            proxy,
            maxCount,
            device_id,
        ) = self.__process_kwargs__(kwargs)
        kwargs["custom_device_id"] = device_id
        query = {"noUser": 1, "userCount": 30, "scene": 0}
        api_url = "{}node/share/discover?{}&{}".format(
            BASE_URL, self.__add_url_params__(), urlencode(query)
        )
        return self.get_data(url=api_url, **kwargs)["body"][1]["exploreList"]

    def discover_music(self, **kwargs) -> dict:
        """Discover page, consists of music"""
        (
            region,
            language,
            proxy,
            maxCount,
            device_id,
        ) = self.__process_kwargs__(kwargs)
        kwargs["custom_device_id"] = device_id
        query = {"noUser": 0, "userCount": 28, "scene": 17}
        api_url = "{}node/share/discover?{}&{}".format(
            BASE_URL, self.__add_url_params__(), urlencode(query)
        )

        return self.get_data(url=api_url, **kwargs)["body"][2]["exploreList"]

    def get_user_object(self, username, **kwargs) -> dict:
        """Gets a user object (dictionary)

        ##### Parameters
        * username: The username of the user
        """
        (
            region,
            language,
            proxy,
            maxCount,
            device_id,
        ) = self.__process_kwargs__(kwargs)
        kwargs["custom_device_id"] = device_id
        return self.get_user(username, **kwargs)["userInfo"]["user"]

    def get_user(self, username, **kwargs) -> dict:
        """Gets the full exposed user object

        ##### Parameters
        * username: The username of the user
        """
        (
            region,
            language,
            proxy,
            maxCount,
            device_id,
        ) = self.__process_kwargs__(kwargs)

        done = False
        n = 1
        while not done:
            try:
                r = requests.get(
                    "https://tiktok.com/@{}?lang=en".format(quote(username)),
                    headers={
                        'authority': 'www.tiktok.com',
                        'pragma': 'no-cache',
                        'cache-control': 'no-cache',
                        'sec-ch-ua': '" Not A;Brand";v="99", "Chromium";v="96", "Google Chrome";v="96"',
                        'sec-ch-ua-mobile': '?0',
                        'sec-ch-ua-platform': '"macOS"',
                        'upgrade-insecure-requests': '1',
                        'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.55 Safari/537.36',
                        'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
                        'sec-fetch-site': 'none',
                        'sec-fetch-mode': 'navigate',
                        'sec-fetch-user': '?1',
                        'sec-fetch-dest': 'document',
                        'accept-language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
                        'cookie': 'tt_csrf_token=AMMycXihaTqIKrrg-htB34U4; csrf_session_id=c116c11802204a77967b41a6fc0f1b19; others_view_mode=grid; _ga=GA1.2.1901867119.1613673590; s_v_web_id=verify_klew60d8_9AqnIlOI_U1J0_4ZVq_8VqA_ha7MCoYjfyhx; webapp_tiktok_lang=ru-RU; cookie-consent={%22ga%22:true%2C%22af%22:true%2C%22fbp%22:true%2C%22lip%22:true%2C%22version%22:%22v2%22}; _abck=607B2F455A80BACB85A48E704EB7D1D3~-1~YAAQr4BtaP5JTlh6AQAA7RfqcAa0Lb9ldLAShw5G7dlQCoc+oWOEi5gJhr0/hmYmyIRBxr7WAwKXRp4dfz5Rak5jKKEMAP7INgLAQNQHtuex+UKH1mRMr2CUzg3IgbJ8K9OVEiZazGFztcBQvTYVUFvWQgYyxmUedx6k6OiUrzXnJQYqd7/MnKfvTeZlOXkrDbw5RsxlZz52weuvft+0cuY/Yx48HaA3oMs1dWGhVoUCWGSWAbf2OfW2VlA4Rdv950J575Me1sEFKZqPHYDm8tKNDnLnmxYibX/5y69cgK4pgJQtFrJ9/9kmNTqqVn0tQnK4bgIcu9/AqRxobsBRZBD5+LCbUhmE8onA8hANC3YSZ9zIWW3/5Foln2s83LDMAyN7r2Cl~-1~-1~-1; custom_slardar_web_id=6893109346227652102; tta_attr_id=0.1628094277.6992611672481333250; tta_attr_id_mirror=0.1628094277.6992611672481333250; MONITOR_DEVICE_ID=05f922ec-82ec-4dd9-9e01-bf9acee80524; csrf_session_id=c116c11802204a77967b41a6fc0f1b19; __tea_sdk__user_unique_id=amp-xjmiB6bCXuuBU-AM7qicNA; d_ticket=283bad69c5f56d2f7dbb7fdd20ae84cd7735c; _gid=GA1.2.1643532504.1631000430; _gat_UA-143770054-3=1; _hjid=02f4385d-8c21-4044-85d7-8fe757694a44; from_way=paid; _fbp=fb.1.1631121449199.755379746; _gat_UA-143770054-2=1; MONITOR_WEB_ID=6893109346227652102; d_ticket_ads=065013a45c8232bed160ececa04299e57735c; tt_webid=6893109346227652102; custom_slardar_web_id=6893109346227652102; passport_csrf_token_default=f4f27d4d24acce4c11a85201393c906c; passport_csrf_token=f4f27d4d24acce4c11a85201393c906c; _tea_utm_cache_1988={%22utm_source%22:%22copy%22%2C%22utm_medium%22:%22ios%22%2C%22utm_campaign%22:%22client_share%22}; _gac_UA-143770054-3=1.1635258647.CjwKCAjwzt6LBhBeEiwAbPGOgUjnvfGH4C3VccXFN-rOnZf0Jhm1fs8Pfc-f7HlvotWEyvCnC-UZ3BoCkkQQAvD_BwE; sso_uid_tt_ads=f95be55730ab777018d12f402374be7d5dd904c705a0b23fc1e893e6c65bcf30; sso_uid_tt_ss_ads=f95be55730ab777018d12f402374be7d5dd904c705a0b23fc1e893e6c65bcf30; toutiao_sso_user_ads=b7244ba078684265838c494da42f6ada; toutiao_sso_user_ss_ads=b7244ba078684265838c494da42f6ada; sid_guard_ads=3612c93bbd16f6ad3a58958d6eebc763%7C1635854968%7C5184000%7CSat%2C+01-Jan-2022+12%3A09%3A28+GMT; uid_tt_ads=0e5a1f267058a6e54308618e0b07431b9501cacb39804ba619e3307b6a6377fe; uid_tt_ss_ads=0e5a1f267058a6e54308618e0b07431b9501cacb39804ba619e3307b6a6377fe; sid_tt_ads=3612c93bbd16f6ad3a58958d6eebc763; sessionid_ads=3612c93bbd16f6ad3a58958d6eebc763; sessionid_ss_ads=3612c93bbd16f6ad3a58958d6eebc763; sid_ucp_v1_ads=1.0.0-KDU2NjczMmI3YjkyMmEwZjBkOTYwYWNjYTVjMDQxZDdlY2JkNTljZTAKGAiCiL-a7-Klm2EQ-NSEjAYYzCQ4AUDrBxABGgNzZzEiIDM2MTJjOTNiYmQxNmY2YWQzYTU4OTU4ZDZlZWJjNzYz; ssid_ucp_v1_ads=1.0.0-KDU2NjczMmI3YjkyMmEwZjBkOTYwYWNjYTVjMDQxZDdlY2JkNTljZTAKGAiCiL-a7-Klm2EQ-NSEjAYYzCQ4AUDrBxABGgNzZzEiIDM2MTJjOTNiYmQxNmY2YWQzYTU4OTU4ZDZlZWJjNzYz; passport_auth_status=074f0d3345389673897657e5a6aa6123%2Cefcf14cb1c16ff07c7dca11ee5cd9da1; passport_auth_status_ss=074f0d3345389673897657e5a6aa6123%2Cefcf14cb1c16ff07c7dca11ee5cd9da1; _tea_utm_cache_3053={%22utm_source%22:%22copy%22%2C%22utm_medium%22:%22ios%22%2C%22utm_campaign%22:%22client_share%22}; odin_tt=a374ed3070c53ca3413586c2c0bb5ef253f6beb6e6be9d7fe0b9c27fe06199ad364da51243f26c95a20c299796c0d0ecd01e1b331817ea2199b649eb64e2f0ecf2435e3a123c680125208b9f08be5692; R6kq3TV7=ALFdCX19AQAAvXyX5whwKgQrgo1Yn20iIdUYAquONVo0cIFFdaC3FFc1p8bo|1|0|bf5fba148d2cf52f13c058ce8475d5a1de1c49c3; __tea_cookie_tokens_1988=%257B%2522web_id%2522%253A%2522%2522%252C%2522timestamp%2522%253A1638480330414%257D; ttwid=1%7C5vEvRhEh7U2QdW5ovKWCI7rD8TsuCIiwO7aus_CBDo0%7C1638480332%7Cab78c19a684b27f5a8598c4f2002f0d52824d2705325384a86b2ddaaed84c4a9; msToken=_FK0r_xdSNqNEbhqnuRiMHiADgx6tvZF-1-mn8iYyYhVtTvC9M52ukxjnCn1EZTjQCvKwI2CXWwnR65CIyC_7r2DlbPtO_C-sr-DIdGqTipeiqGqJZRxov0LaTJp_0ra6e3M9Z94; _abck=607B2F455A80BACB85A48E704EB7D1D3~-1~YAAQqoYe1KmqpNV4AQAAPKZA1gVCacIgaM0AkZbO+rHQgnh2ZjQvSBS9BPOdxpqNhxKEyjkvoysX9ytiBFanKnlOp+2m2kK67R/MxEIYJGuyzGgbJdujKlmadlluo+MLSULqGovvNAuzJZYtBrtcEU3IkYlHq5ucUH6VSP/Q/o+9fKME1GJjijr9PpQNpHtigKtK56GTows1jMAlMRhZdi6qier/KHXEZ91HftbIXFfOAWzpfSV5j2b//23rbk8eKAgT9cBW0TbXomWSANcs3nHc2mcR5I48g6FXjlvnfQAvlGEqqcRvO6H2yFSpHnxixpL5GiUAsMgFZQTdxzRHrnugIH9TLCodxPX7GBIjBT2KQY3ub/MMbhL8DW8h2j6ASDr4PyM=~0~-1~-1; ttwid=1|LufHN_ldtn8OCNkgk-nEN0bOtybGvMes1C-tNeHQNeo|1638480797|d4452095c346f44844dcd919fc90e28725c925dfbd8ebc88ffa2981fb03db6f8'
                    },
                    proxies=self.__format_proxy(kwargs.get("proxy", None)),
                    timeout=10
                )

                t = r.text

                try:
                    j_raw = self.__extract_tag_contents(r.text)
                except IndexError:
                    p = re.compile(r'authorId":"(.*?)","authorSecId":"(.*?)"', re.S)
                    # m = p.findall(r.text)
                    m = p.search(r.text)
                    data = m.groups()
                    user = {"userInfo": {"user": {"id": data[0], "secUid": data[1]}}}
                    return user

                user = json.loads(j_raw)["props"]["pageProps"]

                if user["serverCode"] == 404:
                    raise TikTokNotFoundError(
                        "TikTok user with username {} does not exist".format(username)
                    )

                return user
            except Exception as e:
                r = None
                if not (n % 10):
                    logging.error('retry ' + str(n))
                    logging.error(e)
                n = n + 1
                time.sleep(2)

                if n > 100:
                    return

    def get_suggested_users_by_id(
        self, userId="6745191554350760966", count=30, **kwargs
    ) -> list:
        """Returns suggested users given a different TikTok user.

        ##### Parameters
        * userId: The id of the user to get suggestions for

        * count: The amount of users to return, optional
        """
        (
            region,
            language,
            proxy,
            maxCount,
            device_id,
        ) = self.__process_kwargs__(kwargs)
        kwargs["custom_device_id"] = device_id
        query = {
            "noUser": 0,
            "pageId": userId,
            "userId": userId,
            "userCount": count,
            "scene": 15,
        }
        api_url = "{}node/share/discover?{}&{}".format(
            BASE_URL, self.__add_url_params__(), urlencode(query)
        )
        res = []
        for x in self.get_data(url=api_url, **kwargs)["body"][0]["exploreList"]:
            res.append(x["cardItem"])
        return res[:count]

    def get_suggested_users_by_id_crawler(
        self, count=30, startingId="6745191554350760966", **kwargs
    ) -> list:
        """Crawls for listing of all user objects it can find.

        ##### Parameters
        * count: The amount of users to crawl for

        * startingId: The ID of a TikTok user to start at, optional

            Optional but uses a static one to start, so you may get more
            unique results with setting your own.
        """
        (
            region,
            language,
            proxy,
            maxCount,
            device_id,
        ) = self.__process_kwargs__(kwargs)
        kwargs["custom_device_id"] = device_id
        users = []
        unusedevice_idS = [startingId]
        while len(users) < count:
            userId = random.choice(unusedevice_idS)
            newUsers = self.get_suggested_users_by_id(userId=userId, **kwargs)
            unusedevice_idS.remove(userId)

            for user in newUsers:
                if user not in users:
                    users.append(user)
                    unusedevice_idS.append(user["id"])

        return users[:count]

    def get_suggested_hashtags_by_id(
        self, count=30, userId="6745191554350760966", **kwargs
    ) -> list:
        """Returns suggested hashtags given a TikTok user.

        ##### Parameters
        * userId: The id of the user to get suggestions for
        """
        (
            region,
            language,
            proxy,
            maxCount,
            device_id,
        ) = self.__process_kwargs__(kwargs)
        kwargs["custom_device_id"] = device_id
        query = {
            "noUser": 0,
            "pageId": userId,
            "userId": userId,
            "userCount": count,
            "scene": 15,
        }
        api_url = "{}node/share/discover?{}&{}".format(
            BASE_URL, self.__add_url_params__(), urlencode(query)
        )
        res = []
        for x in self.get_data(url=api_url, **kwargs)["body"][1]["exploreList"]:
            res.append(x["cardItem"])
        return res[:count]

    def get_suggested_hashtags_by_id_crawler(
        self, count=30, startingId="6745191554350760966", **kwargs
    ) -> list:
        """Crawls for as many hashtags as it can find.

        ##### Parameters
        * count: The amount of users to crawl for

        * startingId: The ID of a TikTok user to start at
        """
        (
            region,
            language,
            proxy,
            maxCount,
            device_id,
        ) = self.__process_kwargs__(kwargs)
        kwargs["custom_device_id"] = device_id
        hashtags = []
        ids = self.get_suggested_users_by_id_crawler(
            count=count, startingId=startingId, **kwargs
        )
        while len(hashtags) < count and len(ids) != 0:
            userId = random.choice(ids)
            newTags = self.get_suggested_hashtags_by_id(userId=userId["id"], **kwargs)
            ids.remove(userId)

            for hashtag in newTags:
                if hashtag not in hashtags:
                    hashtags.append(hashtag)

        return hashtags[:count]

    def get_suggested_music_by_id(
        self, count=30, userId="6745191554350760966", **kwargs
    ) -> list:
        """Returns suggested music given a TikTok user.

        ##### Parameters
        * userId: The id of the user to get suggestions for

        * count: The amount of users to return

        * proxy: The IP address of a proxy to make requests from
        """
        (
            region,
            language,
            proxy,
            maxCount,
            device_id,
        ) = self.__process_kwargs__(kwargs)
        kwargs["custom_device_id"] = device_id
        query = {
            "noUser": 0,
            "pageId": userId,
            "userId": userId,
            "userCount": count,
            "scene": 15,
        }
        api_url = "{}node/share/discover?{}&{}".format(
            BASE_URL, self.__add_url_params__(), urlencode(query)
        )

        res = []
        for x in self.get_data(url=api_url, **kwargs)["body"][2]["exploreList"]:
            res.append(x["cardItem"])
        return res[:count]

    def get_suggested_music_id_crawler(
        self, count=30, startingId="6745191554350760966", **kwargs
    ) -> list:
        """Crawls for hashtags.

        ##### Parameters
        * count: The amount of users to crawl for

        * startingId: The ID of a TikTok user to start at
        """
        (
            region,
            language,
            proxy,
            maxCount,
            device_id,
        ) = self.__process_kwargs__(kwargs)
        kwargs["custom_device_id"] = device_id
        musics = []
        ids = self.get_suggested_users_by_id_crawler(
            count=count, startingId=startingId, **kwargs
        )
        while len(musics) < count and len(ids) != 0:
            userId = random.choice(ids)
            newTags = self.get_suggested_music_by_id(userId=userId["id"], **kwargs)
            ids.remove(userId)

            for music in newTags:
                if music not in musics:
                    musics.append(music)

        return musics[:count]

    def get_video_by_tiktok(self, data, **kwargs) -> bytes:
        """Downloads video from TikTok using a TikTok object.

        You will need to set a custom_device_id to do this for anything but trending.
        To do this, this is pretty simple you can either generate one yourself or,
        you can pass the generate_static_device_id=True into the constructor of the
        TikTokApi class.

        ##### Parameters
        * data: A TikTok object

            A TikTok JSON object from any other method.
        """
        (
            region,
            language,
            proxy,
            maxCount,
            device_id,
        ) = self.__process_kwargs__(kwargs)
        kwargs["custom_device_id"] = device_id
        try:
            api_url = data["video"]["downloadAddr"]
        except Exception:
            try:
                api_url = data["itemInfos"]["video"]["urls"][0]
            except Exception:
                api_url = data["itemInfo"]["itemStruct"]["video"]["playAddr"]
        return self.get_video_by_download_url(api_url, **kwargs)

    def get_video_by_download_url(self, download_url, **kwargs) -> bytes:
        """Downloads video from TikTok using download url in a TikTok object

        ##### Parameters
        * download_url: The download url key value in a TikTok object
        """
        (
            region,
            language,
            proxy,
            maxCount,
            device_id,
        ) = self.__process_kwargs__(kwargs)
        kwargs["custom_device_id"] = device_id
        return self.get_bytes(url=download_url, **kwargs)

    def get_video_by_url(self, video_url, **kwargs) -> bytes:
        """Downloads a TikTok video by a URL

        ##### Parameters
        * video_url: The TikTok url to download the video from
        """
        (
            region,
            language,
            proxy,
            maxCount,
            device_id,
        ) = self.__process_kwargs__(kwargs)
        kwargs["custom_device_id"] = device_id

        tiktok_schema = self.get_tiktok_by_url(video_url, **kwargs)
        download_url = tiktok_schema["itemInfo"]["itemStruct"]["video"]["downloadAddr"]

        return self.get_bytes(url=download_url, **kwargs)

    def get_video_no_watermark(self, video_url, return_bytes=1, **kwargs) -> bytes:
        """Gets the video with no watermark
        .. deprecated::

        Deprecated due to TikTok fixing this

        ##### Parameters
        * video_url: The url of the video you want to download

        * return_bytes: Set this to 0 if you want url, 1 if you want bytes
        """
        (
            region,
            language,
            proxy,
            maxCount,
            device_id,
        ) = self.__process_kwargs__(kwargs)
        raise Exception("Deprecated method, TikTok fixed this.")

    def get_music_title(self, id, **kwargs):
        """Retrieves a music title given an ID

        ##### Parameters
        * id: The music id to get the title for
        """
        r = requests.get(
            "https://www.tiktok.com/music/-{}".format(id),
            headers={
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
                "authority": "www.tiktok.com",
                "Accept-Encoding": "gzip, deflate",
                "Connection": "keep-alive",
                "Host": "www.tiktok.com",
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/86.0.4240.111 Safari/537.36",
            },
            proxies=self.__format_proxy(kwargs.get("proxy", None)),
            cookies=self.get_cookies(**kwargs),
            **self.requests_extra_kwargs,
        )
        t = r.text
        j_raw = self.__extract_tag_contents(r.text)

        music_object = json.loads(j_raw)["props"]["pageProps"]["musicInfo"]
        if not music_object.get("title", None):
            raise TikTokNotFoundError("Song of {} id does not exist".format(str(id)))

        return music_object["title"]

    def get_secuid(self, username, **kwargs):
        """Gets the secUid for a specific username

        ##### Parameters
        * username: The username to get the secUid for
        """
        r = requests.get(
            "https://tiktok.com/@{}?lang=en".format(quote(username)),
            headers={
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
                "authority": "www.tiktok.com",
                "path": "/@{}".format(quote(username)),
                "Accept-Encoding": "gzip, deflate",
                "Connection": "keep-alive",
                "Host": "www.tiktok.com",
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/86.0.4240.111 Safari/537.36",
            },
            proxies=self.__format_proxy(
                kwargs.get("proxy", None), cookies=self.get_cookies(**kwargs)
            ),
            **self.requests_extra_kwargs,
        )
        try:
            return r.text.split('"secUid":"')[1].split('","secret":')[0]
        except IndexError as e:
            logging.info(r.text)
            logging.error(e)
            raise Exception(
                "Retrieving the user secUid failed. Likely due to TikTok wanting captcha validation. Try to use a proxy."
            )

    @staticmethod
    def generate_device_id():
        """Generates a valid device_id for other methods. Pass this as the custom_device_id field to download videos"""
        return "".join([random.choice(string.digits) for num in range(19)])

    #
    # PRIVATE METHODS
    #

    def __format_proxy(self, proxy) -> dict:
        """
        Formats the proxy object
        """
        if proxy is None and self.proxy is not None:
            proxy = self.proxy
        if proxy is not None:
            return {"http": proxy, "https": proxy}
        else:
            return None

    def __get_js(self, proxy=None) -> str:
        return requests.get(
            "https://sf16-muse-va.ibytedtos.com/obj/rc-web-sdk-gcs/acrawler.js",
            proxies=self.__format_proxy(proxy),
            **self.requests_extra_kwargs,
        ).text

    def __format_new_params__(self, parm) -> str:
        # TODO: Maybe try not doing this? It should be handled by the urlencode.
        return parm.replace("/", "%2F").replace(" ", "+").replace(";", "%3B")

    def __add_url_params__(self) -> str:
        query = {
            "aid": 1988,
            "app_name": "tiktok_web",
            "device_platform": "web_mobile",
            "region": self.region or "US",
            "priority_region": "",
            "os": "ios",
            "referer": "",
            "root_referer": "",
            "cookie_enabled": "true",
            "screen_width": self.width,
            "screen_height": self.height,
            "browser_language": self.browser_language.lower() or "en-us",
            "browser_platform": "iPhone",
            "browser_name": "Mozilla",
            "browser_version": self.__format_new_params__(self.userAgent),
            "browser_online": "true",
            "timezone_name": self.timezone_name or "America/Chicago",
            "is_page_visible": "true",
            "focus_state": "true",
            "is_fullscreen": "false",
            "history_len": random.randint(0, 30),
            "language": self.language or "en"
        }
        return urlencode(query)

    def __extract_tag_contents(self, html):
        nonce_start = '<head nonce="'
        nonce_end = '">'
        nonce = html.split(nonce_start)[1].split(nonce_end)[0]
        j_raw = html.split(
            '<script id="__NEXT_DATA__" type="application/json" nonce="%s" crossorigin="anonymous">'
            % nonce
        )[1].split("</script>")[0]
        return j_raw

    # Process the kwargs
    def __process_kwargs__(self, kwargs):
        region = kwargs.get("region", "US")
        language = kwargs.get("language", "en")
        proxy = kwargs.get("proxy", None)
        maxCount = kwargs.get("maxCount", 35)

        if kwargs.get("custom_device_id", None) != None:
            device_id = kwargs.get("custom_device_id")
        else:
            if self.custom_device_id != None:
                device_id = self.custom_device_id
            else:
                device_id = "".join(random.choice(string.digits) for num in range(19))
        return region, language, proxy, maxCount, device_id
