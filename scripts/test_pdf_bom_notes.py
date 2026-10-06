import io
import sys
import base64
import zlib
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from backend.pdf_service import build_pdf_document

def test_bom_notes():
    project_data = {
        "id": 1,
        "name": "Projeto Teste",
        "client_name": "Cliente Teste",
        "client_email": "cliente@teste.com",
        "client_phone": "11999999999",
        "status": "draft",
        "notes": "Observação do projeto",
        "summary": {
            "plates_details": [
                {
                    "name": "Placa 1",
                    "quantity": 1,
                    "total_time_hours": 2.0,
                    "filament_material": "PLA",
                    "printer_name": "Bambu Lab X1C",
                    "nozzle_diameter": "0.4",
                    "bed_type": "Textured PEI",
                    "layer_height": "0.20",
                    "unit_print_time_hours": 2.0,
                    "part_weight_g": 50.0,
                    "purge_weight_g": 5.0,
                }
            ],
            "bom_details": [
                {
                    "name": "Parafuso M3x12",
                    "category": "Fixadores",
                    "quantity": 10,
                    "unit_cost": 0.50,
                    "subtotal": 5.00,
                    "notes": "Aco Inox 304 Cabeca Abaulada"
                }
            ],
            "suggested_price": 50.0,
            "final_price_to_client": 50.0,
            "base_cost": 25.0,
        }
    }
    user_data = {
        "full_name": "Test User",
        "company_name": "Test 3D",
        "email": "user@test.com",
    }

    client_pdf = build_pdf_document(project_data, user_data, doc_type="client")
    tech_pdf = build_pdf_document(project_data, user_data, doc_type="technical")

    client_bytes = client_pdf.getvalue()
    tech_bytes = tech_pdf.getvalue()

    def extract_stream_text(raw):
        idx1 = raw.find(b'stream\n') + len(b'stream\n')
        idx2 = raw.find(b'endstream')
        stream_data = raw[idx1:idx2].strip()
        a85 = base64.a85decode(stream_data, adobe=True)
        return zlib.decompress(a85).decode('latin-1')

    client_text = extract_stream_text(client_bytes)
    tech_text = extract_stream_text(tech_bytes)

    assert "Aco Inox 304 Cabeca Abaulada" in client_text, "BOM notes missing from client PDF"
    assert "Aco Inox 304 Cabeca Abaulada" in tech_text, "BOM notes missing from technical sheet"

    # Also test empty plates in technical PDF
    project_data_empty_plates = dict(project_data)
    project_data_empty_plates["summary"] = dict(project_data["summary"])
    project_data_empty_plates["summary"]["plates_details"] = []
    tech_empty_pdf = build_pdf_document(project_data_empty_plates, user_data, doc_type="technical")
    tech_empty_bytes = tech_empty_pdf.getvalue()
    tech_empty_text = extract_stream_text(tech_empty_bytes)
    assert "Nenhuma pe" in tech_empty_text or "Nenhuma" in tech_empty_text, "Empty plates note missing from technical sheet"

    print("All PDF BOM notes and empty plates tests passed successfully!")

if __name__ == "__main__":
    test_bom_notes()
