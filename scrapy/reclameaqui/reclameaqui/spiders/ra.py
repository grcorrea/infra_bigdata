import scrapy
import logging
import os
import sys

class RaSpider(scrapy.Spider):
    name = 'ra'
    empresa = ["santander", "itau", "bradesco", "banco-do-brasil"]
    start_urls = [f'https://www.reclameaqui.com.br/empresa/{empresa}/lista-reclamacoes/']
    page = 1
    last_page = 2
    
    def start_requests(self):
        for emp in self.empresa:
            for i in range(self.page, self.last_page + 1):
                url = f'https://www.reclameaqui.com.br/empresa/{emp}/lista-reclamacoes/?pagina={i}'
                yield scrapy.Request(
                    url=url,
                    callback=self.parse,
                    dont_filter=True,
                    meta={"cookiejar": i}
                )

    def parse(self, response, **kwargs):
        link = {}
        link = response.xpath("//div[@class='sc-1pe7b5t-0 bJdtis']/a/@href").getall()
        complete_link = []
        complete_link = list(map(lambda link: "https://www.reclameaqui.com.br" + link.replace('"', ''), link))

        for d in complete_link:
            yield scrapy.Request(
                url = d,
                callback = self.parse_reclame,
                dont_filter = True,
                meta={'cookiejar': response.meta['cookiejar']}
            )
        
    def parse_reclame(self, response):
        
        company = response.xpath("//a[@data-testid='company-page-link']/text()").get()
        idempresa = response.xpath("//span[@data-testid='complaint-id']/text()").get()
        categoria = response.xpath("//li[@data-testid='listitem-categoria']/div/a/text()").get()
        produto = response.xpath("//li[@data-testid='listitem-produto']/div/a/text()").get()
        problema = response.xpath("//li[@data-testid='listitem-problema']/div/a/text()").get()
        create_date = response.xpath("//span[@data-testid='complaint-creation-date']/text()").get()
        location = response.xpath("//span[@data-testid='complaint-location']/text()").get()
        link = response.url
        titulo = response.xpath("//h1/text()").get()
        comentario = response.xpath("//p[@data-testid='complaint-description']/text()").get()

        yield dict(
            id = idempresa,
            titulo = titulo,
            comentario = comentario,
            empresa = company,
            categoria = categoria,
            produto = produto,
            problema = problema,
            local = location,
            data = create_date,
            link = link
        )