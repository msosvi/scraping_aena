import logging
from selenium import webdriver
from selenium.webdriver.support.ui import Select, WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
import pandas as pd


def get_logger():
    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
                        datefmt='%d-%b-%y %H:%M:%S')
    logger = logging.getLogger('scraping_aena')
    return logger


def main():

    logger = get_logger()

    driver = webdriver.Firefox()
    wait = WebDriverWait(driver, timeout=30)

    driver.get("https://wwwssl.aena.es/csee/Satellite?pagename=Estadisticas/Home")
    logger.info("Terminé de cargar la página")

    driver.quit()


if __name__ == '__main__':
    main()
