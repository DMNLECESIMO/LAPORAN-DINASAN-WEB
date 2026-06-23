import streamlit as st
import pandas as pd
from supabase import create_client, Client
from fpdf import FPDF
import datetime
import calendar

# 1. Inisialisasi Supabase
@st.cache_resource
def init_supabase():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase = init_supabase()

# 2. Membuat Struktur Navigasi Sidebar (Mengembalikan Semua Menu Anda)
st.sidebar.title("Navigasi Aplikasi")
menu = st.sidebar.selectbox(
    "Menu Utama", 
    ["Beranda", "Input Data Karyawan", "Input Laporan Harian", "Pencarian & Cetak PDF"]
)

# ==================== HALAMAN 1: BERANDA ====================
if menu == "Beranda":
    st.title("🚂 Selamat Datang di Web Laporan Pengoperasian KAI")
    st.write("Sistem manajemen data operasional dinasan dan rekapitulasi laporan resmi.")
    st.info("Silakan pilih menu di samping kiri untuk menginput data atau mencetak PDF.")

# ==================== HALAMAN 2: INPUT DATA KARYAWAN ====================
elif menu == "Input Data Karyawan":
    st.title("👥 Input Data Karyawan Baru")
    
    with st.form("form_karyawan", clear_on_submit=True):
        nipp_input = st.text_input("NIPP Karyawan")
        nama_input = st.text_input("Nama Lengkap Karyawan")
        submit_karyawan = st.form_submit_button("Simpan Data Karyawan")
        
        if submit_karyawan:
            if nipp_input and nama_input:
                try:
                    supabase.table("karyawan").insert({"nipp": nipp_input, "nama": nama_input}).execute()
                    st.success(f"Berhasil menambahkan karyawan: {nama_input}")
                except Exception as e:
                    st.error(f"Gagal menyimpan ke database: {e}")
            else:
                st.warning("Mohon isi semua kolom terlebih dahulu.")

# ==================== HALAMAN 3: INPUT LAPORAN HARIAN ====================
elif menu == "Input Laporan Harian":
    st.title("📝 Input Laporan Harian Dinasan")
    
    # Ambil list karyawan untuk pilihan di form
    try:
        karyawan_res = supabase.table("karyawan").select("nipp, nama").execute()
        list_karyawan = karyawan_res.data
    except:
        list_karyawan = []
        
    if list_karyawan:
        dict_karyawan = {k['nama']: k['nipp'] for k in list_karyawan}
        
        with st.form("form_laporan", clear_on_submit=True):
            nama_pilih = st.selectbox("Nama Karyawan", list(dict_karyawan.keys()))
            tgl_input = st.date_input("Tanggal Kegiatan", datetime.date.today())
            jenis_dinasan = st.text_input("Jenis Dinasan (Contoh: DINAS PPKA PAGI)")
            detail_kegiatan = st.text_area("Detail Kegiatan")
            serah_terima = st.text_input("Serah Terima Dinasan")
            
            # Key unik diubah agar tidak memicu DuplicateElementId
            submit_laporan = st.form_submit_button("Simpan Laporan Harian")
            
            if submit_laporan:
                nipp_pilih = dict_karyawan[nama_pilih]
                try:
                    supabase.table("laporan").insert({
                        "nipp": nipp_pilih,
                        "tanggal": str(tgl_input),
                        "jenis_dinasan": jenis_dinasan,
                        "detail_kegiatan": detail_kegiatan,
                        "serah_terima": serah_terima
                    }).execute()
                    st.success("Laporan harian berhasil disimpan ke database!")
                except Exception as e:
                    st.error(f"Gagal menyimpan laporan: {e}")
    else:
        st.warning("Data karyawan belum tersedia. Mohon isi data karyawan terlebih dahulu.")

# ==================== HALAMAN 4: PENCARIAN & CETAK PDF ====================
elif menu == "Pencarian & Cetak PDF":
    st.title("🚂 Web Laporan Pengoperasian KAI")
    st.subheader("🔍 Rekapitulasi Data & Download PDF 4 Halaman")

    try:
        karyawan_res = supabase.table("karyawan").select("nipp, nama").execute()
        list_karyawan = karyawan_res.data
    except Exception as e:
        st.error(f"Gagal mengambil data karyawan: {e}")
        list_karyawan = []

    if list_karyawan:
        dict_karyawan = {k['nama']: k['nipp'] for k in list_karyawan}
        
        col1, col2, col3 = st.columns(3)
        with col1:
            nama_cari = st.selectbox("Nama Karyawan", list(dict_karyawan.keys()), key="sb_cari_nama")
        with col2:
            bln_cari = st.selectbox("Bulan", [f"{i:02d}" for i in range(1, 13)], index=datetime.datetime.now().month - 1, key="sb_cari_bln")
        with col3:
            thn_cari = st.text_input("Tahun", value=str(datetime.datetime.now().year), key="ti_cari_thn")
            
        nipp_cari = dict_karyawan[nama_cari]
        filter_bln = f"{thn_cari}-{bln_cari}"
        
        try:
            last_day = calendar.monthrange(int(thn_cari), int(bln_cari))[1]
        except:
            last_day = 31

        try:
            res_harian = supabase.table("laporan")\
                .select("*")\
                .eq("nipp", nipp_cari)\
                .gte("tanggal", f"{filter_bln}-01")\
                .lte("tanggal", f"{filter_bln}-{last_day}")\
                .order("tanggal")\
                .execute()
                
            data_harian = res_harian.data if res_harian else []
        except Exception as e:
            st.error(f"Error query database: {e}")
            data_harian = []

        if data_harian:
            df = pd.DataFrame(data_harian)
            
            kolom_wajib = ["tanggal", "jenis_dinasan", "detail_kegiatan", "serah_terima"]
            for kol in kolom_wajib:
                if kol not in df.columns:
                    df[kol] = ""
                    
            st.dataframe(df[kolom_wajib], use_container_width=True)
            
            if st.button("🖨️ Urutkan & Cetak PDF Resmi", key="btn_cetak_pdf_utama"):
                pdf = FPDF()
                pdf.add_page()
                
                # Judul PDF
                pdf.set_font("Arial", "B", 14)
                pdf.cell(190, 8, "REKAPITULASI LAPORAN REAL-TIME", ln=True, align='C')
                pdf.ln(5)
                
                # Informasi Karyawan
                pdf.set_font("Arial", "", 10)
                pdf.cell(30, 6, f"Nama: {nama_cari}", ln=True)
                pdf.cell(30, 6, f"NIPP: {nipp_cari}", ln=True)
                pdf.cell(30, 6, f"Periode: {bln_cari}-{thn_cari}", ln=True)
                pdf.ln(5)
                
                # Header Tabel PDF
                pdf.set_font("Arial", "B", 10)
                pdf.cell(30, 8, "Hari/Tanggal", border=1, align='C')
                pdf.cell(50, 8, "Kegiatan", border=1, align='C')
                pdf.cell(50, 8, "Serah Terima", border=1, align='C')
                pdf.cell(60, 8, "Detail/Dokumentasi", border=1, ln=True, align='C')
                
                # Isi Baris Tabel PDF
                pdf.set_font("Arial", "", 9)
                for _, row in df.iterrows():
                    pdf.cell(30, 10, str(row["tanggal"]), border=1, align='C')
                    pdf.cell(50, 10, str(row["jenis_dinasan"])[:25], border=1)
                    pdf.cell(50, 10, str(row["serah_terima"])[:25], border=1)
                    pdf.cell(60, 10, str(row["detail_kegiatan"])[:30], border=1, ln=True)
                
                # Render berkas output secara aman
                try:
                    pdf_content = pdf.output()
                    if isinstance(pdf_content, str):
                        pdf_output = pdf_content.encode('latin-1')
                    else:
                        pdf_output = pdf_content
                except:
                    pdf_output = pdf.output(dest='S')
                    if isinstance(pdf_output, str):
                        pdf_output = pdf_output.encode('latin-1')
                
                st.download_button(
                    label="📥 Download Dokumen PDF Hasil Cetak",
                    data=pdf_output,
                    file_name=f"Laporan_{nama_cari}_{filter_bln}.pdf",
                    mime="application/pdf",
                    key="btn_download_proses"
                )
        else:
            st.info("Belum ada entri data laporan untuk bulan ini.")
    else:
        st.warning("Data karyawan tidak ditemukan di database.")
