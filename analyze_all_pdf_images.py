#!/usr/bin/env python3
"""
Анализатор всех изображений из PDF для восстановления логической цепочки эксплойта
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Any

class PDFImageAnalyzer:
    def __init__(self, base_path: str):
        self.base_path = Path(base_path)
        self.images_path = self.base_path / "complete_pdf_analysis" / "all_images"
        self.analysis_path = self.base_path / "complete_pdf_analysis" / "analysis"
        self.exploit_chain = []
        
    def analyze_exploit_chain(self) -> Dict[str, Any]:
        """Анализирует логическую цепочку эксплойта на основе всех изображений"""
        
        # Загружаем детальный анализ страниц
        with open(self.analysis_path / "pages_detailed_analysis.json", "r", encoding="utf-8") as f:
            pages_analysis = json.load(f)
            
        # Группируем изображения по категориям эксплойта
        exploit_categories = {
            "intro": [],           # Страницы 1-9: Введение, архитектура Solana
            "legacy_exposure": [], # Страницы 10-34: Legacy Data Exposure
            "legacy_interop": [],  # Страницы 35-50: Legacy Interoperability 
            "new_exposure": [],    # Страницы 51-66: New Data Exposure
            "vm_memory": [],       # Страницы 67-89: VM Memory Management
            "new_interop": [],     # Страницы 90-108: New Interoperability
            "bug_chain": [],       # Страницы 109-142: Bug chain
            "exploit": []          # Страницы 143-165: Exploit
        }
        
        # Классифицируем страницы
        for page in pages_analysis:
            page_num = page["page_number"]
            
            if page_num <= 9:
                exploit_categories["intro"].append(page)
            elif page_num <= 34:
                exploit_categories["legacy_exposure"].append(page)
            elif page_num <= 50:
                exploit_categories["legacy_interop"].append(page)
            elif page_num <= 66:
                exploit_categories["new_exposure"].append(page)
            elif page_num <= 89:
                exploit_categories["vm_memory"].append(page)
            elif page_num <= 108:
                exploit_categories["new_interop"].append(page)
            elif page_num <= 142:
                exploit_categories["bug_chain"].append(page)
            else:
                exploit_categories["exploit"].append(page)
                
        # Анализ логической цепочки
        exploit_chain = {
            "title": "Pwning Blockchain for Fun and Profit - Solana RCE Exploit Chain",
            "vulnerability": "CVE in Solana validator leading to RCE",
            "exploit_flow": []
        }
        
        # 1. Основа эксплойта - понимание архитектуры
        exploit_chain["exploit_flow"].append({
            "stage": 1,
            "name": "Understanding Solana Architecture",
            "pages": "1-9",
            "key_concepts": [
                "AccountSharedData structure",
                "Program execution model",
                "Transaction model",
                "Memory management"
            ],
            "images": self._get_images_for_pages(1, 9)
        })
        
        # 2. Legacy Data Exposure - первая уязвимость
        exploit_chain["exploit_flow"].append({
            "stage": 2,
            "name": "Legacy Data Exposure",
            "pages": "10-34",
            "key_concepts": [
                "Account serialization vulnerabilities",
                "AccountInfo construction bugs",
                "Write permission check bypass",
                "Memory layout exploitation"
            ],
            "critical_finding": "Unsafe memory exposure through legacy AccountInfo",
            "images": self._get_images_for_pages(10, 34)
        })
        
        # 3. Legacy Interoperability - расширение атаки
        exploit_chain["exploit_flow"].append({
            "stage": 3,
            "name": "Legacy Interoperability (CPI)",
            "pages": "35-50",
            "key_concepts": [
                "Cross-Program Invocation (CPI) vulnerabilities",
                "CPI return value manipulation",
                "Account state corruption through CPI"
            ],
            "critical_finding": "CPI can be abused to corrupt account states",
            "images": self._get_images_for_pages(35, 50)
        })
        
        # 4. New Data Exposure - современные уязвимости
        exploit_chain["exploit_flow"].append({
            "stage": 4,
            "name": "New Data Exposure",
            "pages": "51-66",
            "key_concepts": [
                "New account serialization bugs",
                "Copy-on-Write (CoW) vulnerabilities",
                "Reserved data buffer exploitation"
            ],
            "critical_finding": "New serialization format still vulnerable",
            "images": self._get_images_for_pages(51, 66)
        })
        
        # 5. VM Memory Management - ключ к RCE
        exploit_chain["exploit_flow"].append({
            "stage": 5,
            "name": "VM Memory Management Exploitation",
            "pages": "67-89",
            "key_concepts": [
                "Memory Regions manipulation",
                "Direct Mapping vulnerabilities",
                "Host_Addr update bugs",
                "MemoryRegion.State manipulation"
            ],
            "critical_finding": "VM memory regions can be corrupted",
            "images": self._get_images_for_pages(67, 89)
        })
        
        # 6. New Interoperability - усиление атаки
        exploit_chain["exploit_flow"].append({
            "stage": 6,
            "name": "New Interoperability Exploitation",
            "pages": "90-108",
            "key_concepts": [
                "New CPI implementation bugs",
                "MemoryRegion.Host_Addr update vulnerabilities",
                "Guest address validation bypass"
            ],
            "critical_finding": "Missing guest address validation",
            "images": self._get_images_for_pages(90, 108)
        })
        
        # 7. Bug Chain - объединение уязвимостей
        exploit_chain["exploit_flow"].append({
            "stage": 7,
            "name": "Bug Chain Construction",
            "pages": "109-142",
            "key_concepts": [
                "Missing check of guest address when updating MemoryRegion",
                "Out of bounds write to Account2 Databuf",
                "Memory corruption chain"
            ],
            "critical_finding": "Multiple bugs can be chained for memory corruption",
            "images": self._get_images_for_pages(109, 142)
        })
        
        # 8. Final Exploit - достижение RCE
        exploit_chain["exploit_flow"].append({
            "stage": 8,
            "name": "Final Exploit - Arbitrary Read/Write to RCE",
            "pages": "143-165",
            "key_concepts": [
                "Matching MemoryRegion for controlled memory",
                "Cell<u64> manipulation for arbitrary read/write",
                "0xdeadbeef marker for exploit verification",
                "RCE achievement through memory corruption"
            ],
            "critical_finding": "Arbitrary read/write leads to RCE in Solana validator",
            "images": self._get_images_for_pages(143, 165)
        })
        
        # Ключевые техники для реализации
        exploit_chain["implementation_techniques"] = {
            "memory_exploit": [
                "Guest address validation bypass",
                "MemoryRegion manipulation", 
                "Cell<u64> arbitrary read/write",
                "VM heap corruption"
            ],
            "validator_exploit": [
                "Validator memory corruption",
                "RCE through corrupted memory regions",
                "Process control hijacking"
            ],
            "account_exploit": [
                "AccountInfo serialization bugs",
                "Write permission bypass",
                "Account state manipulation"
            ],
            "program_exploit": [
                "CPI vulnerabilities",
                "Program state corruption",
                "Cross-program attacks"
            ]
        }
        
        return exploit_chain
    
    def _get_images_for_pages(self, start: int, end: int) -> List[str]:
        """Получает список изображений для диапазона страниц"""
        images = []
        for page in range(start, end + 1):
            # Проверяем все возможные изображения для страницы
            for i in range(1, 10):  # До 9 изображений на странице
                img_name = f"page_{page:03d}_img_{i:02d}.png"
                img_path = self.images_path / img_name
                if img_path.exists():
                    images.append(img_name)
        return images
    
    def save_analysis(self, output_file: str):
        """Сохраняет анализ в файл"""
        analysis = self.analyze_exploit_chain()
        
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(analysis, f, ensure_ascii=False, indent=2)
            
        # Также создаем текстовый отчет
        report_file = output_file.replace(".json", "_report.md")
        with open(report_file, "w", encoding="utf-8") as f:
            f.write("# Solana RCE Exploit Chain Analysis\n\n")
            f.write(f"## {analysis['title']}\n\n")
            f.write(f"**Vulnerability**: {analysis['vulnerability']}\n\n")
            
            f.write("## Exploit Flow\n\n")
            for stage in analysis["exploit_flow"]:
                f.write(f"### Stage {stage['stage']}: {stage['name']}\n")
                f.write(f"**Pages**: {stage['pages']}\n\n")
                
                f.write("**Key Concepts**:\n")
                for concept in stage["key_concepts"]:
                    f.write(f"- {concept}\n")
                f.write("\n")
                
                if "critical_finding" in stage:
                    f.write(f"**Critical Finding**: {stage['critical_finding']}\n\n")
                    
                f.write(f"**Images**: {len(stage['images'])} images\n\n")
                f.write("---\n\n")
                
            f.write("## Implementation Techniques\n\n")
            for module, techniques in analysis["implementation_techniques"].items():
                f.write(f"### {module}\n")
                for technique in techniques:
                    f.write(f"- {technique}\n")
                f.write("\n")

if __name__ == "__main__":
    analyzer = PDFImageAnalyzer(r"x:\SOFT\Разработка\solana_token_deployer")
    analyzer.save_analysis(r"x:\SOFT\Разработка\solana_token_deployer\complete_pdf_analysis\exploit_chain_analysis.json")
    print("Анализ логической цепочки эксплойта завершен!")
