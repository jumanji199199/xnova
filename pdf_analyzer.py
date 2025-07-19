"""
PDF Analyzer для изучения блокчейн эксплойтов
Извлекает текст и изображения из PDF документов
"""

import fitz  # PyMuPDF
import os
from pathlib import Path
import json
from typing import Dict, List, Any
import base64
from PIL import Image
import io

class PDFAnalyzer:
    def __init__(self, pdf_path: str):
        self.pdf_path = pdf_path
        self.doc = fitz.open(pdf_path)
        self.total_pages = len(self.doc)
        
    def extract_page_content(self, page_num: int) -> Dict[str, Any]:
        """Извлекает содержимое страницы: текст и изображения"""
        if page_num >= self.total_pages:
            return None
            
        page = self.doc[page_num]
        
        # Извлекаем текст
        text = page.get_text()
        
        # Извлекаем изображения
        images = []
        image_list = page.get_images()
        
        for img_index, img in enumerate(image_list):
            xref = img[0]
            pix = fitz.Pixmap(self.doc, xref)
            
            if pix.n - pix.alpha < 4:  # GRAY or RGB
                img_data = pix.tobytes("png")
                images.append({
                    'index': img_index,
                    'size': (pix.width, pix.height),
                    'data': base64.b64encode(img_data).decode()
                })
            pix = None
            
        return {
            'page_num': page_num + 1,
            'text': text,
            'images': images,
            'image_count': len(images)
        }
    
    def extract_all_content(self) -> List[Dict[str, Any]]:
        """Извлекает содержимое всех страниц"""
        all_content = []
        
        for page_num in range(self.total_pages):
            content = self.extract_page_content(page_num)
            if content:
                all_content.append(content)
                print(f"Обработана страница {page_num + 1}/{self.total_pages}")
                
        return all_content
    
    def save_images_from_page(self, page_num: int, output_dir: str = "extracted_images"):
        """Сохраняет изображения со страницы в файлы"""
        os.makedirs(output_dir, exist_ok=True)
        
        page = self.doc[page_num]
        image_list = page.get_images()
        
        for img_index, img in enumerate(image_list):
            xref = img[0]
            pix = fitz.Pixmap(self.doc, xref)
            
            if pix.n - pix.alpha < 4:
                img_filename = f"page_{page_num + 1}_img_{img_index + 1}.png"
                img_path = os.path.join(output_dir, img_filename)
                pix.save(img_path)
                print(f"Сохранено изображение: {img_path}")
            pix = None
    
    def analyze_blockchain_content(self, page_content: Dict[str, Any]) -> Dict[str, Any]:
        """Анализирует содержимое на предмет блокчейн эксплойтов"""
        text = page_content['text'].lower()
        
        # Ключевые слова для поиска
        exploit_keywords = [
            'exploit', 'vulnerability', 'attack', 'hack', 'reentrancy',
            'overflow', 'underflow', 'flash loan', 'arbitrage', 'mev',
            'sandwich', 'frontrun', 'backrun', 'liquidity', 'slippage',
            'solana', 'ethereum', 'defi', 'smart contract', 'token',
            'pool', 'swap', 'dex', 'amm', 'oracle'
        ]
        
        found_keywords = [kw for kw in exploit_keywords if kw in text]
        
        # Поиск кода или адресов
        has_code = any(pattern in text for pattern in ['0x', 'function', 'contract', 'address'])
        has_solana_addresses = any(len(word) > 40 and word.isalnum() for word in text.split())
        
        return {
            'page_num': page_content['page_num'],
            'exploit_keywords': found_keywords,
            'keyword_count': len(found_keywords),
            'has_code': has_code,
            'has_solana_addresses': has_solana_addresses,
            'text_length': len(page_content['text']),
            'image_count': page_content['image_count'],
            'relevance_score': len(found_keywords) + (2 if has_code else 0) + page_content['image_count']
        }
    
    def get_most_relevant_pages(self, min_score: int = 3) -> List[Dict[str, Any]]:
        """Находит наиболее релевантные страницы для изучения эксплойтов"""
        relevant_pages = []
        
        for page_num in range(self.total_pages):
            content = self.extract_page_content(page_num)
            if content:
                analysis = self.analyze_blockchain_content(content)
                if analysis['relevance_score'] >= min_score:
                    relevant_pages.append({
                        'content': content,
                        'analysis': analysis
                    })
        
        # Сортируем по релевантности
        relevant_pages.sort(key=lambda x: x['analysis']['relevance_score'], reverse=True)
        return relevant_pages
    
    def close(self):
        """Закрывает PDF документ"""
        self.doc.close()

def main():
    pdf_path = "Ginoah-pwning_blockchain_for_fun_and_profit.pdf"
    
    if not os.path.exists(pdf_path):
        print(f"PDF файл не найден: {pdf_path}")
        return
    
    analyzer = PDFAnalyzer(pdf_path)
    print(f"Загружен PDF: {pdf_path}")
    print(f"Всего страниц: {analyzer.total_pages}")
    
    # Находим наиболее релевантные страницы
    print("\nПоиск релевантных страниц...")
    relevant_pages = analyzer.get_most_relevant_pages(min_score=2)
    
    print(f"\nНайдено {len(relevant_pages)} релевантных страниц:")
    
    for i, page_data in enumerate(relevant_pages[:10]):  # Показываем топ-10
        analysis = page_data['analysis']
        print(f"\n--- Страница {analysis['page_num']} (Релевантность: {analysis['relevance_score']}) ---")
        print(f"Ключевые слова: {', '.join(analysis['exploit_keywords'])}")
        print(f"Изображений: {analysis['image_count']}")
        print(f"Есть код: {'Да' if analysis['has_code'] else 'Нет'}")
        
        # Показываем первые 200 символов текста
        text_preview = page_data['content']['text'][:200].replace('\n', ' ')
        print(f"Превью: {text_preview}...")
        
        # Сохраняем изображения с этой страницы
        if analysis['image_count'] > 0:
            analyzer.save_images_from_page(analysis['page_num'] - 1)
    
    # Сохраняем детальный анализ в JSON
    analysis_data = {
        'pdf_info': {
            'filename': pdf_path,
            'total_pages': analyzer.total_pages,
            'relevant_pages_count': len(relevant_pages)
        },
        'relevant_pages': [
            {
                'page_num': page['analysis']['page_num'],
                'relevance_score': page['analysis']['relevance_score'],
                'keywords': page['analysis']['exploit_keywords'],
                'text': page['content']['text'][:1000],  # Первые 1000 символов
                'image_count': page['analysis']['image_count']
            }
            for page in relevant_pages
        ]
    }
    
    with open('pdf_analysis.json', 'w', encoding='utf-8') as f:
        json.dump(analysis_data, f, ensure_ascii=False, indent=2)
    
    print(f"\nДетальный анализ сохранен в pdf_analysis.json")
    analyzer.close()

if __name__ == "__main__":
    main()
