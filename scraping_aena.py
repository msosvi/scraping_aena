import logging
from selenium import webdriver
from selenium.webdriver.support.ui import Select, WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
import numpy as np
import pandas as pd
import time
import datetime


# noinspection PyArgumentList
def get_logger():
    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
                        datefmt='%d-%b-%y %H:%M:%S',
                        handlers=[logging.FileHandler("logs/scraping_aena.log"), logging.StreamHandler()]
                        )
    return logging.getLogger('scraping_aena')


def comprobacion_parametros_respuesta(parametros_respuesta, movimiento, aeropuerto, year):
    if parametros_respuesta['Movimiento'] != movimiento:
        logger.warning("El parametro 'Movimiento' no coincide en la búsqueda y la respuesta:")
        logger.warning("  - Búsqueda: {} - Respuesta: {}".format(movimiento, parametros_respuesta['Movimiento']))

    if parametros_respuesta['Aeropuerto Base'] != aeropuerto:
        logger.warning("El parametro 'Aeropuerto Base' no coincide en la búsqueda y la respuesta:")
        logger.warning("  - Búsqueda: {} - Respuesta: {}".format(aeropuerto, parametros_respuesta['Aeropuerto Base']))

    if year == datetime.datetime.now().year:
        if parametros_respuesta['CONSULTA'] != 'Datos Provisionales Año en Curso':
            logger.warning("La consulta no ha devuelto datos para el año {} ({}).".
                           format(year, parametros_respuesta['CONSULTA']))
    else:
        if parametros_respuesta['CONSULTA'] != "{} - Datos Definitivos".format(year):
            logger.warning("La consulta no ha devuelto los datos para el año {} ({}).".
                           format(year, parametros_respuesta['CONSULTA']))


def comprobacion_numero_filas_resultado(filas_resultados, numero_resultados):
    if len(filas_resultados) - 1 != numero_resultados:
        logger.warning("El número de resultados de la búsqueda ({}) no es igual al número de filas recuperadas ({})".
                       format(numero_resultados, len(filas_resultados) - 1))


def comprobacion_numero_registros_df(df, numero_resultados):
    if len(df) != numero_resultados:
        logger.warning("El número de resultados de la búsqueda ({}) no es igual al número de registro recuperados ({})".
                       format(numero_resultados, len(df)))


def recuperar_datos_busqueda(fila_encabezado, filas_resultados):
    encabezado_busqueda = fila_encabezado.text.lower().split(" ")
    encabezado_busqueda.insert(0, "airline")

    df = pd.DataFrame([], columns=encabezado_busqueda)

    for fila in filas_resultados[:-1]:
        valores = []
        casillas = fila.find_elements_by_tag_name("td")
        for c in casillas:
            valor = c.get_attribute('textContent')
            if valor != '':
                valores.append(valor)

        df.loc[len(df)] = valores

    # Añado las columnas que el resutado de la búsqueda puede no dar al no tener datos.
    encabezado_completo = ['airline', 'total', 'ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sep', 'oct',
                           'nov', 'dic']
    df = df.reindex(columns=encabezado_completo, fill_value='--')
    return df


def aplicar_tipo_numerico(df, columnas_numericas):
    df[columnas_numericas] = df[columnas_numericas].apply(
        lambda x: x.str.replace(r'\.', '').replace('--', np.NaN).astype(float).astype('Int64'))
    return df


def get_text_options(select):
    text_options = []
    for option in select.options:
        text_options.append(option.text)

    # No devuelvo la primera optición que se corresponde con 'todos'
    return text_options[1:]


def get_select_tipo_consulta(driver):
    return Select(driver.find_element_by_id('dssid'))


def get_select_agrupacion(driver):
    return Select(driver.find_element_by_xpath("//select[@id='selectObjetos'][@title='Agrupación']"))


def get_select_aeropuerto(driver):
    return Select(driver.find_element_by_xpath("//select[@id='selectElementos'][@title='Aeropuerto Base']"))


def get_select_movimiento(driver):
    return Select(driver.find_element_by_xpath("//select[@id='selectElementos'][@title='Movimiento']"))


def get_select_year(driver):
    return Select(driver.find_element_by_xpath("//select[@id='selectElementos'][@title='Año']"))


def get_fila_encabezado(driver):
    """Recuperamos la fila de encabezado.
    La necesitamos porque si un mes no tiene datos la tabla de resultado no incluye la columna.
    Usamos la fila anterior que tiene el texto Pasajeros para localizarla."""

    return driver.find_element_by_xpath("//tr/td[text()='Pasajeros']/../following-sibling::tr")


def get_filas_resultados(driver):
    """Recuperamos las filas de la tabla de resultados
    # Las filas de la tabla de respuesta tienen como id campo de agrupación,
    # para nuestro caso todos los ids empiezan con 'NOMBRE COMPAÑIA:"""

    return driver.find_elements_by_xpath("//tr[starts-with(@id,'NOMBRE COMPAÑIA:')]")


def get_parametros_respuesta(driver):
    """Devuelve un diccionario con los parámetros usados en la consulta a partir del texto
    con el filtro de la consulta que devuelve la página."""

    texto_filtro = driver.find_element_by_xpath("//td[starts-with(text(),'CONSULTA:')]").text

    # La descripción de la consulta para los años anteriores incluye el texto 'Año:', los dos puntos
    # impide el correcto troceado.
    texto_filtro = str.replace(texto_filtro, "Año:", "")

    d = dict(item.split(":") for item in texto_filtro.split(","))
    parametros_respuesta = dict(zip(list(k.strip() for k in d.keys()),
                                    (list(v.strip() for v in d.values()))))

    return parametros_respuesta


def abrir_pagina_estadistica(driver, wait, tipo):

    driver.get("https://wwwssl.aena.es/csee/Satellite?pagename=Estadisticas/Home")
    logger.info("Página incial de Estadísticas de tráfico aéreo de AENA cargada.")

    if tipo == 'AÑO_ACTUAL':
        select_id = 'estadoactual'
        open_script = 'abrirEnlaceComboestadoactual()'
        logger.info("Incio de la carga de la página de estadísticas del año en curso por pasajeros.")
    else:
        select_id = 'traficoanio'
        open_script = 'abrirEnlaceCombotraficoanio()'
        logger.info("Incio de la carga de la página de estadísticas de los años anteriores por pasajeros.")

    select_estadistica = Select(driver.find_element_by_id(select_id))
    select_estadistica.select_by_visible_text("1. Pasajeros")
    driver.execute_script(open_script)
    # Usamos el botón de búsqueda como indicador de que la página está cargada.
    wait.until(EC.element_to_be_clickable((By.XPATH, "//a[@href ='javascript:buscar();']")))
    logger.info("Fin de la carga de la página de estadísticas.")


def pivot_longer(wide_df):

    # Dicionario para convertir las abreviaturas de los meses a números
    meses = {'ene': '01', 'feb': '02', 'mar': '03', 'abr': '04', 'may': '05', 'jun': '06', 'jul': '07',
             'ago': '08', 'sep': '09', 'oct': '10', 'nov': '11', 'dic': '12'}

    long_df = wide_df.rename(columns=meses).drop(columns=["total"]).melt(
                        id_vars=['airline', 'movimiento', 'aeropuerto', 'year'],
                        var_name='mes',
                        value_name='num_pasajeros')

    long_df.insert(loc=3, column='fecha', value=long_df.year.astype(str) + '-' + long_df.mes)
    long_df = long_df.drop(columns=['year', 'mes'])
    long_df = long_df.dropna()

    return long_df


def scraping_year(driver, wait, year):

    if year == datetime.datetime.now().year:
        abrir_pagina_estadistica(driver, wait, 'AÑO_ACTUAL')
    else:
        abrir_pagina_estadistica(driver, wait, 'AÑOS_ANTERIORES')
        # En la busqueda de años anteriores hay que especificar el año.
        select_year = get_select_year(driver)
        select_year.select_by_visible_text(str(year))

    # Recuperamos los select de los campos que vamos a usar para las búsquedas de datos.
    select_tipo_consulta = get_select_tipo_consulta(driver)
    select_agrupacion = get_select_agrupacion(driver)
    select_aeropuerto = get_select_aeropuerto(driver)
    select_movimiento = get_select_movimiento(driver)

    # Parámetros para la búsqueda de datos
    select_tipo_consulta.select_by_visible_text("1. Pasajeros")
    select_agrupacion.select_by_visible_text("NOMBRE COMPAÑIA")

    aeropuertos = get_text_options(select_aeropuerto)
    movimientos = get_text_options(select_movimiento)

    # TODO Quitar limitación de parametros para las pruebas
    # aeropuertos = aeropuertos[:2]
    aeropuertos = ['LA PALMA', 'EL HIERRO']
    movimientos = ['LLEGADA']

    df = None
    for aeropuerto in aeropuertos:
        for movimiento in movimientos:
            logger.info("Sleeping...")
            time.sleep(5)

            # Tenemos que volver a coger los campos select ya que la página se actualiza después de cada búsqueda.
            select_aeropuerto = get_select_aeropuerto(driver)
            select_movimiento = get_select_movimiento(driver)

            logger.info("Inicio de la búsqueda de datos para: {} - {}.".format(aeropuerto, movimiento))

            select_aeropuerto.select_by_visible_text(aeropuerto)
            select_movimiento.select_by_visible_text(movimiento)

            driver.execute_script('buscar()')

            # Usamos el texto con el resultado de la búsqueda como indicador de que ha terminado.
            casilla_numero_resultados = wait.until(
                EC.visibility_of_element_located((By.XPATH, "//td[contains(text(),'resultados encontrados')]")))

            numero_resultados = int(casilla_numero_resultados.text.split()[0])
            logger.info("Fin de la búsqueda. {} resultados encontrados.".format(numero_resultados))

            if numero_resultados > 0:
                # Esperamos a que la carga de resultados termine para recuperar todas las filas.
                # Usamos la fila de totales como indicador.
                fila_total = wait.until(
                    EC.visibility_of_element_located((By.XPATH, "//tr[starts-with(@id,'NOMBRE COMPAÑIA:Total')]")))

                fila_encabezado = get_fila_encabezado(driver)

                filas_resultados = get_filas_resultados(driver)
                comprobacion_numero_filas_resultado(filas_resultados, numero_resultados)

                parametros_respuesta = get_parametros_respuesta(driver)
                comprobacion_parametros_respuesta(parametros_respuesta, movimiento, aeropuerto, year)

                logger.info("Inicio de la recuperación de los resultados de la búsqueda.")
                df_busqueda = recuperar_datos_busqueda(fila_encabezado, filas_resultados)
                # TODO comprobacion_totales(df, fila_total)

                # Añadimos columnas al dataframe para los parámetros usados en la consulta:
                # el aeropuerto, el tipo de movimiento y el año.

                df_busqueda.insert(loc=1, column='year', value=year)
                df_busqueda.insert(loc=1, column='aeropuerto', value=parametros_respuesta['Aeropuerto Base'])
                df_busqueda.insert(loc=1, column='movimiento', value=parametros_respuesta['Movimiento'])

                logger.info("Fin de la recuperación de los datos de la búsqueda")

                columnas_numericas = ['total', 'ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sep', 'oct',
                                      'nov', 'dic']
                df_busqueda = aplicar_tipo_numerico(df_busqueda, columnas_numericas)

                df = pd.concat([df, df_busqueda], axis=0)
                logger.info("Número total de registros recuperados {}.".format(len(df)))

            # Como usamos el texto de 'resultados encontrados' para idenficar que la búsqueda ha terminado
            # lo quitamos antes de hacer la siguiente búsqueda.
            driver.execute_script("arguments[0].innerText = 'Iniciando nueva busqueda...'", casilla_numero_resultados)

    return df


def main():
    driver = webdriver.Firefox()
    wait = WebDriverWait(driver, timeout=30)

    wide_df = None
    long_df = None
    for year in range(2019, 2021):
        logger.info("Búsqueda de resultados para el año {}".format(year))
        df_year = scraping_year(driver, wait, year)
        df_year.to_pickle("datos/movimento_pasajeros_ancha_{}.pkl".format(year))
        wide_df = pd.concat([wide_df, df_year], axis=0)

        long_df_year = pivot_longer(df_year)
        long_df_year.to_pickle("datos/movimento_pasajeros_larga{}.pkl".format(year))
        long_df = pd.concat([long_df, long_df_year], axis=0)

    logger.info("Exportación del conjunto de datos.")
    wide_df.to_csv("datos/movimientos_pasajeros_ancha.csv", index=False)
    long_df.to_csv("datos/movimientos_pasajeros_larga.csv", index=False)

    logger.info("Fin.")
    driver.quit()


if __name__ == '__main__':
    logger = get_logger()
    main()
