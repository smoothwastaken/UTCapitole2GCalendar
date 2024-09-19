import json
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

from bs4 import BeautifulSoup

from gcsa.google_calendar import GoogleCalendar
from gcsa.event import Event

from dotenv import load_dotenv
import math
import os
import time
import datetime
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

class ScrapperCalendar(object):

  status = 0

  def __init__(self, logger, page: int = 1) -> None:
    """Initializes the ScrapperCalendar object.

    Args:
        logger (Logger()): The logger object.
        page (int, optional): The page to scrap. Defaults to 1.
    """
    # Creating the logger
    self.logger = logger
    self.logger.info("Starting Scrapper...")
    
    # Loading the environment variables
    load_dotenv()
    
    # Getting the page selected
    self.selectedPage = page
    
    # Confirming the start of the scrapper
    self.status = 1
    self.logger.success("Scrapper started!")

  def start(self):
    """Starts the scrapper.
    """
    self.createScrapperOptions()
    self.createScrapperDriver()
    self.loggingIn()
    self.getSelectedPage()
    self.getPageSourceCode()
    events = self.parsePageCode()
    
    return events
    
  def createScrapperOptions(self) -> None:
    """Creates the scrapper options.
    """
    self.chrome_options = Options()
    self.chrome_options.add_argument('-headless')
    self.chrome_options.add_argument('--no-sandbox')
    self.chrome_options.add_argument('--disable-dev-shm-usage')
    self.chrome_options.add_argument("start-maximized")
    self.chrome_options.add_argument("--user-data-dir=selenium")

  def createScrapperDriver(self) -> None:
    """Creates the scrapper driver.
    """
    self.driver = webdriver.Chrome(options=self.chrome_options)

  def loggingIn(self) -> None:
    """Gets the scrapper logged in.
    """
    self.logger.info("Getting logged in...")
    self.logger.info("Getting the page...")
    
    self.driver.get("https://ade-production.ut-capitole.fr/direct/myplanning.jsp")
    
    # Waiting for the page to load
    self.driver.implicitly_wait(300)
    
    self.logger.success("Page loaded!")
    
    # Finding the logging form
    self.logger.info("Finding the logging form...")
    
    self.usernameForm = self.driver.find_element(By.ID, "username")
    self.passwordForm = self.driver.find_element(By.ID, "password")
    self.submitButton = self.driver.find_element(By.ID, "connexion")
    
    self.logger.success("Logging form found!")
    
    # Filling the form
    self.logger.info("Filling the form...")
    
    self.usernameForm.send_keys(os.getenv("USERNAME_KEY"))
    self.passwordForm.send_keys(os.getenv("PASSWORD_KEY"))
    
    self.logger.success("Form filled!")
    
    # Submitting the form
    self.logger.info("Submitting the form...")
    
    self.submitButton.click()
    
    self.logger.success("Form submitted!")
  
    self.logger.info("Waiting for the page to load...")
    # Waiting for the element to be present on the page
    WebDriverWait(self.driver, 30).until(
      EC.presence_of_element_located((By.ID, "Planning"))
    )
    self.logger.success("Page loaded!")
    
  def getSelectedPage(self) -> None:
    """Gets the scrapper selected page.
    """
    
    # Get the button container
    buttonContainer = self.driver.find_element(By.ID, "x-auto-31")
    
    # Get all the button inside the button container using self.driver
    buttons = buttonContainer.find_elements(By.TAG_NAME, "button")
    
    selectableButtons = []
    
    for button in buttons:
      if button.text.strip() != "":
        selectableButtons.append(button)
        
    # Click the selected button
    selectableButtons[self.selectedPage - 1].click()
    
    time.sleep(2)
    
  def getPageSourceCode(self) -> None:
    """Gets the scrapper fetch page code.
    """
    self.logger.info("Fetching the page code...")
    
    self.pageCode = self.driver.page_source
    
    self.driver.quit()
    
    self.logger.success("Page code fetched!")

  def parsePageCode(self) -> list:
    """Parses the page code.
    """
    self.logger.info("Parsing the page code...")
    
    events = Parser.parseEvents(sourceCode=self.pageCode)
    
    self.logger.success("Page code parsed!")
    
    return events
    
class Parser(object):
  
  @staticmethod
  def parseEvents(sourceCode: str) -> list:
    """Parses the events from the source code.

    Args:
        sourceCode (str): The source code of the page.

    Returns:
        list: The list of events.
    """
    
    logger = Logger()
    logger.info("Parsing the events...")
    
    # Using BeautifulSoup to parse the page code
    soup = BeautifulSoup(sourceCode, "html.parser")
    
    # Initializing the event list
    events = []
    
    # Getting the first day number of the week (Monday) and formatting it to a datetime object
    firstDayDate = Parser.parseFirstDayDate(sourceCode=sourceCode)
    firstDayDate = datetime.datetime(year=firstDayDate[0], month=firstDayDate[1], day=firstDayDate[2])
    
    
    # Getting the events (divs with style containing "cursor: auto; position: absolute; left:")
    for event in soup.find_all("div", style=lambda value: value and "cursor: auto; position: absolute; left:" in value):
      logger.success("Event found!")
      
      # Creating the event object
      eventObj = {
        "name": "",
        "description": "",
        "location": "",
        "startDate": datetime.datetime(year=firstDayDate.year, month=firstDayDate.month, day=firstDayDate.day),
        "endDate": datetime.datetime(year=firstDayDate.year, month=firstDayDate.month, day=firstDayDate.day),
      }
      
      # Updating the event object with the date and time of the event
      eventDay, eventTime = Parser.parseTimeOfEvent(event=event.prettify())
      eventObj["startDate"] = eventObj["startDate"] + datetime.timedelta(days=eventDay)
      eventObj["startDate"] = eventObj["startDate"] + datetime.timedelta(hours=eventTime)
      
      # Updating the event object with the end date and time of the event
      eventDuration = Parser.parseEventDuration(event=event.prettify())
      eventObj["endDate"] = eventObj["startDate"] + datetime.timedelta(hours=eventDuration)
      
      # Updating the event object with the name of the event
      eventObj["name"] = Parser.parseNameEvent(event=event.prettify())
      
      # Updating the event object with the location of the event
      eventObj["location"] = Parser.parseEventLocation(event=event.prettify())
      
      # Updating the event object with the description of the event
      eventObj["description"] = Parser.parseEventDescription(event=event.prettify())
    
      # Updating the event dictionary
      events.append(eventObj)
      
      
    return events
  
  @staticmethod
  def parseNameEvent(event: str) -> str:
    """Parses the name of the event.

    Args:
        event (str): The event.

    Returns:
        str: The name of the event.
    """
    logger = Logger()
    logger.info("Parsing the name of the event...")
    
    # Using BeautifulSoup to parse the event
    soup = BeautifulSoup(event, "html.parser")
    
    # Getting the name of the event
    eventName = soup.find("b", class_="eventText").text.strip()
    
    logger.success("Name of the event parsed!")
    
    return eventName
      
  @staticmethod
  def parseEventLocation(event: str) -> str:
    """Parses the location of the event.

    Args:
        event (str): The event.

    Returns:
        str: The location of the event.
    """
    
    logger = Logger()
    logger.info("Parsing the location of the event...")
    
    # Using BeautifulSoup to parse the event
    soup = BeautifulSoup(event, "html.parser")
    
    # Getting the name of the event
    eventLocation = event.split("<br/>")[1].strip()
    
    logger.success("Location of the event parsed!")
    
    return eventLocation
    
  @staticmethod
  def parseEventDescription(event: str) -> str:
    """Parses the description of the event.

    Args:
        event (str): The event.

    Returns:
        str: The description of the event.
    """
    
    logger = Logger()
    logger.info("Parsing the description of the event...")
    
    # Using BeautifulSoup to parse the event
    soup = BeautifulSoup(event, "html.parser")
    
    # Getting the name of the event
    eventDescription = event.split("<br/>")[2:]
    newEventDescription = eventDescription
    i = 0
    for line in eventDescription:
      if (line.strip() != ""):
        newEventDescription[i] = line.strip()
        i += 1
    for _ in range(len(eventDescription) - i + 1):
      newEventDescription.pop()
      
    eventDescription = "\n".join(newEventDescription)
    
    logger.success("Location of the event parsed!")
    
    return eventDescription
  
  @staticmethod
  def parseTimeOfEvent(event: str) -> tuple:
    """Parses the time of the event.

    Args:
        event (str): The event.

    Returns:
        tuple: The day and time of the event.
    """
    
    logger = Logger()
    logger.info("Parsing the time of the event...")
    
    # Using BeautifulSoup to parse the event
    soup = BeautifulSoup(event, "html.parser")
    
    # Find the main div
    mainDiv = soup.find("div")
    
    # Getting the style of the main div
    style = mainDiv["style"]
    
    # Getting the value for the top that contains the time
    eventTime = (((int(style.split(" ")[-1][:-3]) / 30) + 7) // 0.5) * 0.5
    
    # Getting the value for the left that contains the day
    eventDay = int(style.split(" ")[-3][:-3]) // 229
    
    logger.success("Time of the event parsed!")
    
    return (eventDay, eventTime)

  @staticmethod
  def parseEventDuration(event: str) -> float:
    """Parses the duration of the event.

    Args:
        event (str): The event.

    Returns:
        float: The duration of the event.
    """
    
    logger = Logger()
    logger.info("Parsing the duration of the event...")
    
    # Using BeautifulSoup to parse the event
    soup = BeautifulSoup(event, "html.parser")
    
    # Getting the name of the event
    eventDuration = soup.find("table", class_="event")["style"].split(":")[-1][:-2].strip()
    _, eventDuration = float(eventDuration) / 15,6 * 0.25
    
    logger.success("Duration of the event parsed!")
    
    return eventDuration

  @staticmethod
  def parseFirstDayDate(sourceCode: str) -> list:
    """Parses the first day date.

    Args:
        sourceCode (str): The source code of the page.

    Returns:
        list: The first day date.
    """
    
    logger = Logger()
    logger.info("Parsing the first week day date...")
    
    soup = BeautifulSoup(sourceCode, "html.parser")
    
    # Getting the first day number of the week (Monday)
    mondayDate = soup.find("div", id="4")
    mondayDateYear = int(mondayDate.prettify().split("/")[-2][:-2].strip())
    mondayDateMonth = int(mondayDate.prettify().split("/")[-3].strip())
    mondayDateDay = int(mondayDate.prettify().split("/")[-4][-2:].strip())
    
    logger.success("First week day date parsed!")
    
    return [mondayDateYear, mondayDateMonth, mondayDateDay]

class Logger(object):

  types = {
    "info": "[i]",
    "warning": "[!]",
    "success": "[+]",
    "error": "[x]",
  }

  def __init__(self, enable: bool = LOGS):
    """Initializes the Logger object.

    Args:
        enable (bool, optional): The enable status of the logger. Defaults to LOGS.
    """
    self.enable = enable
    if self.enable:
      self.success("Logger started!")

  def format(self, text: str, type: str) -> str:
    """Formats the text.

    Args:
        text (str): The text to format.
        type (str): The type of the text.

    Returns:
        str: The formatted text.
    """
    current_time = datetime.datetime.now().strftime("%H:%M:%S")
    return f"{current_time} {self.types[type]} {text}"

  def log(self, text: str, type: str) -> None:
    """Logs the text.

    Args:
        text (str): The text to log. 
        type (str): The type of the text.
    """
    print(self.format(text=text, type=type))

  def info(self, text: str) -> None:
    """Logs the text as an info.

    Args:
        text (str): The text to log.
    """
    self.log(text=text, type="info")

  def warning(self, text: str) -> None:
    """Logs the text as a warning.

    Args:
        text (str): The text to log.
    """
    self.log(text=text, type="warning")

  def success(self, text: str) -> None:
    """Logs the text as a success.

    Args:
        text (str): The text to log.
    """
    self.log(text=text, type="success")

  def error(self, text: str) -> None:
    """Logs the text as an error.

    Args:
        text (str): The text to log.
    """
    self.log(text=text, type="error")

class GCalendar(object):
  
  status = 0
  
  def __init__(self, events: list, config: dict) -> None:
    """Initializes the GCalendar object.

    Args:
        events (list): The list of events.
    """
    # Creating the logger
    self.logger = logger
    self.logger.info("Starting GCalendar...")
    
    # Loading the configuration into the class
    self.config = config
    
    # Loading the environment variables
    load_dotenv()
    
    # Logging in to the Google Calendar
    self.calendar = GoogleCalendar(self.config["googleEmail"], credentials_path=self.config["googleCredentialsFile"])
    self.calendarId = self.calendar.get_calendar_list()
    for calendar in self.calendarId:
      if calendar.summary == self.config["googleCalendarName"]:
        self.calendarId = calendar.id
        break
    
    # Getting the events
    self.events = events
    
    # Confirming the start of the scrapper
    self.status = 1
    self.logger.success("GCalendar started!")
    
  def addAllEvents(self) -> None:
    """Adds all the events to the Google Calendar
    """
    for event in self.events:
      self.addEvent(event=event)
      
  def addEvent(self, event: dict):
    """Adds an event to the Google Calendar.

    Args:
        event (dict): The event to add.
    """
    self.logger.info(f"Adding the event {event['name']}...")
    
    # Creating the event
    new_event = Event(
      event["name"],
      start=event["startDate"],
      end=event["endDate"],
      description=event["description"],
      location=event["location"],
    )
    
    # Adding the event to the calendar
    createdEvent = self.calendar.add_event(new_event)
    self.calendar.move_event(createdEvent, self.calendarId)
    
  def deleteAllEvents(self) -> None:
    """Deletes all the events from the Google Calendar that are from the specified calendar.
    """
    
    self.logger.info("Deleting all the events...")
    
    allPreviousEvents = self.calendar.get_events(time_min=self.events[0]["startDate"], calendar_id=self.calendarId, )
    for previousEvent in allPreviousEvents:
      self.logger.info(f"Deleting the event {previousEvent.summary} from {previousEvent.start} to {previousEvent.end} (event id : {previousEvent.id})...")
      try:
        self.calendar.delete_event(event=previousEvent, calendar_id=self.calendarId)
      except Exception as e:
        self.logger.error(f"Event {previousEvent.summary} not deleted or already deleted! Passing...")
        self.logger.error(f"Error : {e}")
        continue
      self.logger.success(f"Event {previousEvent.summary} deleted!")
      
      
    self.logger.success("All the events deleted!")
    
  def start(self) -> int:
    """Starts the GCalendar.
    """
    self.deleteAllEvents()
    self.addAllEvents()
    return 1

if __name__ == "__main__":
  # Loading the environment variables
  load_dotenv()
  
  # Loading the configuration
  config = None
  with open("config.json", "r") as configFile:
    config = json.load(configFile)
    configFile.close()
    
  # Starting the logger
  logger = Logger(enable=config["log"])
  
  # Loop (through the pages)
  for i in range(1, 8):
    # Initializing the scrapper
    scrapper = ScrapperCalendar(logger=logger, page=i)
    
    # Starting the scrapper
    events = scrapper.start()
    
    # Initializing the GCalendar class
    gcal = GCalendar(events=events, config=config)
    
    # Starting the GCalendar class
    gcal.start()