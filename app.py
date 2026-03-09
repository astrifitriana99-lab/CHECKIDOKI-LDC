import streamlit as st
import google.generativeai as genai
import fitz  # PyMuPDF
import warnings

st.set_page_config(page_title="LDC Document Auditor Ultra", page_icon="🚢", layout="wide")
warnings.filterwarnings("ignore", category=FutureWarning)

# --- CONFIGURATION ---
try:
    API_KEY = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=API_KEY)
except:
    st.error("API Key belum disetting di Secrets!")

def get_active_model():
    return 'gemini-1.5-pro'

def extract_pdf_hybrid(pdf_file):
    doc = fitz.open(stream=pdf_file.read(), filetype="pdf")
    image_parts = []
    extracted_text = ""
    
    for page in doc:
        # 1. SEDOT TEKS DIGITAL ASLI (Akurasi 100% untuk PDF Sistem)
        extracted_text += page.get_text("text") + "\n"
        
        # 2. AMBIL GAMBARNYA (Untuk melihat posisi dan layout tabel)
        pix = page.get_pixmap(matrix=fitz.Matrix(3.0, 3.0)) 
        img_data = pix.tobytes("jpg")
        image_parts.append({"mime_type": "image/jpeg", "data": img_data})
        
    return image_parts, extracted_text

# --- UI ---
st.title("🚢 LDC Auditor - Ultra Precision Mode")

with st.sidebar:
    st.header("Instruksi Khusus")
    notes = st.text_area("Tambahkan catatan tambahan:", height=150)
    st.success("Mode Hybrid aktif: AI membaca Layout (Gambar) + Karakter Asli (Teks) secara bersamaan.")

uploaded_files = st.file_uploader("Upload PDF Dokumen Ekspor", type=['pdf'], accept_multiple_files=True)

if st.button("JALANKAN AUDIT SEKARANG", type="primary"):
    if not uploaded_files:
        st.error("Upload file dulu ya!")
    else:
        with st.status("AI sedang mengekstrak teks asli dan menganalisa dokumen...", expanded=True) as status:
            try:
                model = genai.GenerativeModel(get_active_model())
                
                prompt_parts = [
                    "Kamu adalah Senior Auditor Ekspor paling teliti. Tugasmu adalah Zero Tolerance Error!\n"
                    "PERHATIAN: Saya melampirkan teks asli dari dokumen DAN gambar layoutnya. "
                    "Gunakan TEKS ASLI sebagai acuan utama jika gambarnya kurang jelas (Jangan sampai SOO terbaca SOH).\n"
                    "1. IDENTIFIKASI MASTER: File 'BL' atau 'Bill of Lading' adalah kebenaran mutlak.\n"
                    "2. ALAMAT SHIPPER PATEN (Wajib Sama Persis):\n"
                    "   PT. LDC TRADING INDONESIA\n"
                    "   GEDUNG WISMA 46 - KOTA BNI LANTAI 15 SUITE 15.01, 15.10-12\n"
                    "   JL JEND. SUDIRMAN KAV 1, KARET TENGSIN, TANAH ABANG,\n"
                    "   KOTA ADM. JAKARTA PUSAT, DKI JAKARTA, 10220, INDONESIA\n"
                    "3. DATA WAJIB AUDIT:\n"
                    "   - SHIPPER, CONSIGNEE, GROSS & NET WEIGHT, MARKING, VESSEL, VOYAGE, LOADING, DISCHARGE, CONTAINER & SEAL NUMBER.\n"
                    "4. INSTRUKSI KHUSUS:\n"
                    "   - Cek angka koma dan titik pada Weight. Beda 0.01 pun ERROR.\n"
                    "   - Pastikan nomor Container dan Seal tidak kurang atau lebih 1 digit.\n"
                    "   - Bandingkan semua dokumen pendukung terhadap MASTER BL.\n\n"
                    "FORMAT TABEL:\n"
                    "| Field | Data Master (BL) | Data Dokumen Ini | Status | Solusi |\n"
                    "| :--- | :--- | :--- | :--- | :--- |\n"
                    f"CATATAN TAMBAHAN: {notes}"
                ]

                for uploaded_file in uploaded_files:
                    st.write(f"🔍 Mengekstrak Hybrid: {uploaded_file.name}")
                    
                    # Kita masukkan gambar DAN teks aslinya ke AI
                    img_parts, raw_text = extract_pdf_hybrid(uploaded_file)
                    
                    prompt_parts.append(f"\n--- TEKS DIGITAL ASLI DARI FILE: {uploaded_file.name} ---\n")
                    prompt_parts.append(raw_text)
                    prompt_parts.append(f"\n--- GAMBAR LAYOUT DARI FILE: {uploaded_file.name} ---\n")
                    prompt_parts.extend(img_parts)

                response = model.generate_content(prompt_parts)
                
                status.update(label="Analisa Selesai!", state="complete", expanded=False)
                st.markdown(response.text)
                
            except Exception as e:
                st.error(f"Error: {e}")
