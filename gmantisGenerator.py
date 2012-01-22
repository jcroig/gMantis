#!/usr/bin/env python
# encoding: utf-8
"""
gmantisGenerator.py

Created by Juan Carlos Roig on 2011-12-16.
Copyright (c) 2011 __MyCompanyName__. All rights reserved.
"""

from BeautifulSoup import BeautifulSoup
from mako.template import Template
from datetime import datetime
from datetime import date
import urllib, urllib2, cookielib
import re
import ConfigParser
import codecs

TEMPLATE_FILE = 'template.html'

class Project:
    def __init__(self):
        self.id = None
        self.description = None

    def __str__(self):
        result = ""
        for key in self.__dict__:
            result += " " + key + ": " + str(self.__dict__[key])

        return 'Project(' + result.strip() + ')'

class ProjectBuilder:
    def __init__(self, html):
        self.html = html

    def build(self):
        project = Project()
        project.id = str(self.html['value'].encode('utf-8')).strip()
        project.description = str(self.html.text.encode('utf-8')).replace('&nbsp;&raquo;', '').strip()
        return project
        

class Mantis:
    def __init__(self):
        self.id = None
        self.project = None
        self.fecha_envio = None
        self.categoria = None
        self.severidad = None
        self.resumen = None 
        self.estado = None
        self.jira = None

    def toJSON(self):
        json = '{"id": ' + str(self.id) + ','
        json += '"fechaEnvio": new Date(' + str(self.fecha_envio.year) + ',' + str(self.fecha_envio.month-1) + ',' + str(self.fecha_envio.day) + '),' 
        json += '"categoria": ' + '"' + self.categoria.decode('utf-8') + '",'
        json += '"severidad": ' + '"' + self.severidad + '",'
        json += '"estado": ' + '"' + self.estado + '",'
        json += '"resumen": ' + '"' + self.resumen.decode('utf-8') + '"}'
		
        return json
        
    def __str__(self):
        result = ""
        for key in self.__dict__:
            result += " " + key + ": " + str(self.__dict__[key])

        return 'Mantis(' + result.strip() + ')'

class MantisBuilder:
    def __init__(self, html):
        self.html = html

    def build(self):
        mantis = Mantis()
        selected_project = self.html.find('select', attrs={'name': 'project_id'}).find('option', attrs={'selected': 'selected'})
        mantis.project = ProjectBuilder(selected_project).build()
        table_data = self.html('table')[2]

        fila2 = table_data('tr')[2]
        mantis.id = str(int(fila2('td')[0].text))

        categoria = str(fila2('td')[1].text.encode('utf-8'))
        mantis.categoria = categoria[categoria.find(']') + 1:].strip()

        fecha_envio = str(fila2('td')[4].text).split()[0].split('-')
        mantis.fecha_envio = date(int(fecha_envio[0]), int(fecha_envio[1]), int(fecha_envio[2]))

        mantis.severidad = str(fila2('td')[2].text)

        fila7 = table_data('tr')[7]
        mantis.estado = str(fila7('td')[1].text)

        fila9 = table_data('tr')[9]
        resumen = str(fila9('td')[1].text.encode('utf-8')).strip()
        
        if ":" in resumen:
            resumen = resumen[resumen.find(":") + 1:].strip()

        mantis.resumen = resumen

        fila25 = table_data('tr')[25]
        mantis.jira = str(fila25('td')[1].text).strip()

        return mantis
    
class MantisScrapper:
    def __init__(self, ip, port, username, password):
        cj = cookielib.CookieJar()
        self.opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cj))
        self.base_url = 'http://' + ip + ':' + port + '/mantis'
        login_data = urllib.urlencode({'username' : username, 'password' : password})
        self.opener.open(self.base_url + '/login.php', login_data)

    def change_project(self, project_id):
        self.opener.open(self.base_url + '/set_project.php', urllib.urlencode({'project_id': project_id}))
    
    def get_mantis(self, id):
        html = self.fetch_url(self.base_url + '/view.php', {'id' : id})
        mantis = MantisBuilder(html).build()
        print str(mantis)
        return mantis
    
    def get_all_mantis(self, project_id):
        result = []
        self.change_project(project_id)
        params = {'per_page' : '500', 'type' : '1'}
        html = self.fetch_url(self.base_url + '/view_all_set.php?f=3', params)
        pagination = html.findAll('a', attrs={'href' : re.compile("view_all_bug_page.php\?page_number=\d+")})
        if len(pagination) > 0:
            pages = int(pagination[-1]['href'].split("=")[1])
        else:
            pages = 1

        for page in xrange(1, pages + 1):
            html = self.fetch_url(self.base_url + '/view_all_bug_page.php?page_number=' + str(page), params)		
            mantis_list = [tag['value'] for tag in html.findAll('input', attrs={'name': 'bug_arr[]', 'type': 'checkbox'})]

            for id in mantis_list:
                result.append(self.get_mantis(id)) 

        return result

    def get_projects(self):
        result = []
        for option in self.fetch_url(self.base_url + '/view_all_set.php?f=3').find('select', attrs={'name': 'project_id'}).findAll('option'):
            result.append(ProjectBuilder(option).build())

        return result

    def fetch_url(self, url, params=None, parsed=True):
        if (params == None):            
            resp = self.opener.open(url)
        else:
            resp = self.opener.open(url, urllib.urlencode(params))

        result = resp.read()
        if parsed:    
            return BeautifulSoup(result)
        else:
            return result

    def __del__(self):
        self.opener.close()

def main():
    t = datetime.now()

    config = ConfigParser.RawConfigParser()
    config.read('config.cfg')
    server = config.get('server', 'address')
    port = config.get('server', 'port')
    if server == '' or port == '':
        print 'Error! Configuración incorrecta. Revise el fichero de configuración config.cfg'
        return

    print 'Usuario: ',
    user = raw_input()

    print 'Password: ',
    password = raw_input()

    sc = MantisScrapper(server, port, user, password)

    projects = sc.get_projects()
    for project in xrange(len(projects)):
        print str(project) + ' -> ' + projects[project].description    

    print 'Seleccione un proyecto: ',
    project = projects[int(raw_input())]
    print 'Extrayendo informacion del proyecto ' + project.description + ' ...'

    template = Template(filename=TEMPLATE_FILE, input_encoding='utf-8', output_encoding='utf-8')
    html = template.render(mantis=sc.get_all_mantis(project.id), title=project.description + ' ' + t.strftime('%d-%m-%Y %H:%M'))
    report_filename = 'gMantis' + project.description + t.strftime('%Y%m%d%H%M') + '.html'
    page_file = codecs.open(report_filename,'w', 'utf-8')
    page_file.write(html.decode('utf-8'))
    page_file.close()

    print 'Finalizado! Creado fichero ' + report_filename

if __name__ == '__main__':
    main()
