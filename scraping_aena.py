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
    return logging.getLogger('scraping_aena')


def get_parametros_respuesta(texto_filtro):
    """Convierte el texto con el filtro de la consulta en un
    diccionario de parámetros de la respuesta"""

    d = dict(item.split(":") for item in texto_filtro.split(","))
    parametros_respuesta = dict(zip(list(k.strip() for k in d.keys()),
                                    (list(v.strip() for v in d.values()))))

    return parametros_respuesta


def comprobacion_resultados(filas_resultados, numero_resultados, parametros_respuesta, movimiento, aeropuerto):
    """Comprobación de resultados. Número de resultados y parámetros."""
    if len(filas_resultados) - 1 != numero_resultados:
        logger.warning("El número de resultados de la búsqueda ({}) no es igual al numero de filas recuperadas ({})".
                       format(numero_resultados, len(filas_resultados) - 1))

    if (parametros_respuesta['Movimiento'] != movimiento or
            parametros_respuesta['Aeropuerto Base'] != aeropuerto):
        logger.warning("Los parámetros de la búsqueda y de la respuesta no coinciden:")
        logger.warning("    - Movimiento: {} - {}".format(movimiento, parametros_respuesta['Movimiento']))
        logger.warning("    - Aeropuerto {} - {}".format(aeropuerto, parametros_respuesta['Aeropuerto Base']))


def recuperar_datos_busqueda(filas_resultados):
    df = pd.DataFrame([], columns=["airline", "total", "1", "2", "3", "4", "5", "6", "7", "8", "9"])

    for fila in filas_resultados[:-1]:
        valores = []
        casillas = fila.find_elements_by_tag_name("td")
        for c in casillas:
            valor = c.get_attribute('textContent')
            if valor != '':
                valores.append(valor)

        df.loc[len(df)] = valores
    return df


def main():
    driver = webdriver.Firefox()
    wait = WebDriverWait(driver, timeout=30)

    driver.get("https://wwwssl.aena.es/csee/Satellite?pagename=Estadisticas/Home")
    logger.info("Fin de la carga de la página inicial.")

    select_estado_actual = Select(driver.find_element_by_id('estadoactual'))
    select_estado_actual.select_by_visible_text("1. Pasajeros")

    logger.info("Incio de la carga de la página de estadísticas del año en curso por pasajeros")
    driver.execute_script('abrirEnlaceComboestadoactual()')
    # Usamos el botón de búsqueda como indicador de que la página está cargada.
    wait.until(EC.element_to_be_clickable((By.XPATH, "//a[@href ='javascript:buscar();']")))
    logger.info("Fin de la carga de la página de estadísticas del año en curso por pasajeros")

    # Recuperamos los select de los campos que vamos a usar para las búsquedas de datos.
    select_tipo_consulta = Select(driver.find_element_by_id('dssid'))
    select_agrupacion = Select(driver.find_element_by_xpath("//select[@id='selectObjetos'][@title='Agrupación']"))

    select_aeropuerto = Select(
        driver.find_element_by_xpath("//select[@id='selectElementos'][@title='Aeropuerto Base']"))
    select_movimiento = Select(driver.find_element_by_xpath("//select[@id='selectElementos'][@title='Movimiento']"))

    # Parámetros de para la búsqueda de datos
    select_tipo_consulta.select_by_visible_text("1. Pasajeros")
    select_agrupacion.select_by_visible_text("NOMBRE COMPAÑIA")

    # TODO A partir de aquí tenemos que poner el bucle para recuperar los datos de todos los aeropuertos.
    aeropuerto = "LA PALMA"
    movimiento = "LLEGADA"

    select_aeropuerto.select_by_visible_text(aeropuerto)
    select_movimiento.select_by_visible_text(movimiento)

    logger.info("Inicio de la búsqueda de datos para: {} - {}".format(aeropuerto, movimiento))
    driver.execute_script('buscar()')

    # Usamos el texto con el resultado de la búsqueda como indicador de que ha terminado.
    casilla_numero_resultados = wait.until(
        EC.visibility_of_element_located((By.XPATH, "//td[contains(text(),'resultados encontrados')]")))

    numero_resultados = int(casilla_numero_resultados.text.split()[0])
    logger.info("Fin de la búsqueda. {} resultados encontrados.".format(numero_resultados))

    # Recuperamos las filas de la tabla de resultados
    # Las filas de la tabla de respuesta tienen como id campo de agrupación,
    # para nuestro caso todos los ids empiezan con 'NOMBRE COMPAÑIA:"

    filas_resultados = driver.find_elements_by_xpath("//tr[starts-with(@id,'NOMBRE COMPAÑIA:')]")

    texto_filtro = driver.find_element_by_xpath("//td[starts-with(text(),'CONSULTA:')]").text
    parametros_respuesta = get_parametros_respuesta(texto_filtro)

    comprobacion_resultados(filas_resultados, numero_resultados, parametros_respuesta, movimiento, aeropuerto)

    df = recuperar_datos_busqueda(filas_resultados)

    # TODO Conversión de datos en el dataframe
    # TODO convertir la tabla en una tabla larga

    # Añadimos columnas al dataframe para los páramtros usados en la consulta: el aeropuerto y el tipo de movimiento.
    df['movimiento'] = parametros_respuesta['Movimiento']
    df['aeropuerto'] = parametros_respuesta['Aeropuerto Base']

    df.to_csv("pasajeros_prueba.csv")

    driver.quit()


if __name__ == '__main__':
    logger = get_logger()
    main()
