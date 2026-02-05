import io
from fpdf import FPDF

def test_pdf_generation():
    print("Testing FPDF output type...")
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font('Arial', 'B', 16)
    pdf.cell(40, 10, 'Hello World!')
    
    try:
        # detailed debug
        output = pdf.output(dest='S')
        print(f"Output type with dest='S': {type(output)}")
        
        # This simulates what might be happening in the app or what we want to test
        # In FPDF 1.7.2, default output() returns a string (latin-1 encoded bytes masquerading as string in Py3 sometimes, or just string)
        
        raw_output = pdf.output(dest='S')
        
        # strict check for io.BytesIO
        try:
            io.BytesIO(raw_output)
            print("io.BytesIO(raw_output) SUCCESS")
        except TypeError as e:
            print(f"io.BytesIO(raw_output) FAILED: {e}")
            
        # PROPOSED FIX: encode to latin-1
        try:
            encoded_output = raw_output.encode('latin-1')
            io.BytesIO(encoded_output)
            print("io.BytesIO(raw_output.encode('latin-1')) SUCCESS")
        except Exception as e:
            print(f"io.BytesIO(raw_output.encode('latin-1')) FAILED: {e}")

    except Exception as e:
        print(f"General Error: {e}")

if __name__ == "__main__":
    test_pdf_generation()
