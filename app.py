import time
import streamlit as st
import google.generativeai as genai
import fitz  # PyMuPDF
import warnings

# Konfigurasi Tampilan Web
st.set_page_config(page_title="LDC Document Auditor", page_icon="🚢", layout="wide")

# Sembunyikan Warning
warnings.filterwarnings("ignore", category=FutureWarning)

# --- 1. SETTING API KEY ---
# Mengambil API Key dari Streamlit Secrets
try:
    API_KEY = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=API_KEY)
except:
    st.error("API Key belum disetting di Secrets!")

@st.cache_resource 
def get_active_model():
    try:
        # AI akan otomatis mencari nama 'flash' yang paling valid di versimu
        models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        
        # Prioritaskan cari model flash
        for m in models:
            if 'gemini-1.5-flash' in m: 
                return m 
                
        # Kalau flash nggak ada, cari pro
        for m in models:
            if 'gemini-1.5-pro' in m: 
                return m
                
        return models[0]
    except: 
        # Fallback cadangan
        return 'gemini-1.5-flash-latest'

def pdf_to_images(pdf_file):
    doc = fitz.open(stream=pdf_file.read(), filetype="pdf")
    image_parts = []
    extracted_text = ""
    for page in doc:
        # 1. SEDOT TEKS DIGITAL ASLI (Akurasi 100% untuk PDF Sistem)
        extracted_text += page.get_text("text") + "\n"
        
        # 2. AMBIL GAMBARNYA (Untuk melihat posisi dan layout tabel)
        pix = page.get_pixmap(matrix=fitz.Matrix(2.0, 2.0)) 
        img_data = pix.tobytes("jpg")
        image_parts.append({"mime_type": "image/jpeg", "data": img_data})
        
    return image_parts

# --- UI STREAMLIT ---
st.title("🚢 LDC Senior Auditor AI")
st.markdown("Automated Export Document Verification System")

with st.sidebar:
    st.header("Instruksi Khusus")
    notes = st.text_area("Tambahkan catatan audit (Misal: Cek tanggal Sanitary Cert):", height=150)
    st.info("Pastikan upload MASTER BL sebagai acuan utama.")

uploaded_files = st.file_uploader("Upload Dokumen PDF (BL, COO, Phyto, dll)", type=['pdf'], accept_multiple_files=True)

if st.button("MULAI AUDIT DOKUMEN", type="primary"):
    if not uploaded_files:
        st.error("Silakan upload minimal satu file PDF.")
    else:
        with st.status("Sedang memproses dokumen...", expanded=True) as status:
            try:
                model_name = get_active_model()
                model = genai.GenerativeModel(model_name)
                
                # BAGIAN INSTRUKSI (PROMPT)
                prompt_parts = [
                    "Kamu adalah Senior Auditor Ekspor paling teliti. Tugasmu adalah Zero Tolerance Error!\n"
                    "1. IDENTIFIKASI MASTER: File 'BL' atau 'Bill of Lading' adalah kebenaran mutlak.\n"
                    "2. ALAMAT SHIPPER PATEN (Wajib Sama Persis):\n"
                    "   PT. LDC TRADING INDONESIA\n"
                    "   GEDUNG WISMA 46 - KOTA BNI LANTAI 15 SUITE 15.01, 15.10-12\n"
                    "   JL JEND. SUDIRMAN KAV 1, KARET TENGSIN, TANAH ABANG,\n"
                    "   KOTA ADM. JAKARTA PUSAT, DKI JAKARTA, 10220, INDONESIA\n"
                    "3. DATA WAJIB AUDIT:\n"
                    "   - SHIPPER, CONSIGNEE, notify, loading, discharge, marks, vessel, voyage, description of goods, GROSS & NET WEIGHT, CONTAINER & SEAL NUMBER.\n"
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
                    st.write(f"📂 Membaca: {uploaded_file.name}")
                    img_parts = pdf_to_images(uploaded_file)
                    prompt_parts.extend(img_parts)

                st.write("🤖 AI sedang menganalisa data...")

                try:
                    response = model.generate_content(prompt_parts)
                except Exception as api_error:
                    if "429" in str(api_error):
                        st.warning("Kuota penuh, menunggu 10 detik sebelum mencoba lagi...")
                        time.sleep(10)
                        response = model.generate_content(prompt_parts)
                    else:
                        raise api_error

                # Update status dan tampilkan hasil
                status.update(label="Audit Selesai!", state="complete", expanded=False)
                st.markdown("### 📋 Hasil Laporan Audit")
                st.markdown(response.text)
                
            except Exception as e:
                st.error(f"Terjadi kesalahan: {e}")
