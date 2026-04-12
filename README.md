# GSTR-3B Consolidator 📊

A powerful web application built with Streamlit that automatically consolidates multiple GSTR-3B returns into a professional Excel report.

## Features ✨

- ✅ **Upload Multiple PDFs** - Process one or multiple GSTR-3B PDF returns at once
- ✅ **Automatic Data Extraction** - Intelligently extracts key financial data from PDFs
- ✅ **Consolidated Excel Report** - Creates a professional, formatted Excel spreadsheet
- ✅ **Real-time Processing** - Progress tracking and immediate feedback
- ✅ **Data Preview** - View extracted data before generating the final report
- ✅ **Auto-calculated Totals** - Automatic sum formulas in the Excel output
- ✅ **Professional Formatting** - Color-coded headers, proper alignment, and number formatting
- ✅ **Local Processing** - All files are processed locally - no data sent to external servers
- ✅ **User-Friendly Interface** - Modern, intuitive UI with clear instructions

## What It Does

This application:
1. Accepts GSTR-3B PDF returns (any number of months)
2. Extracts key financial data including:
   - Outward supplies (taxable, zero-rated, nil/exempt)
   - Inward supplies and reverse charge data
   - Tax amounts (IGST, CGST, SGST)
3. Creates a consolidated Excel spreadsheet with:
   - Organized data by month
   - Proper number formatting (currency)
   - Automatic total calculations
   - Professional styling

## System Requirements 📋

- Python 3.8 or higher
- pip (Python package manager)
- 500MB free disk space

## Installation & Setup 🚀

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/gstr3b-consolidator.git
cd gstr3b-consolidator
```

### 2. Create a Virtual Environment (Recommended)

**On Windows:**
```bash
python -m venv venv
venv\Scripts\activate
```

**On macOS/Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Run the Application

```bash
streamlit run app.py
```

The application will open in your default web browser at `http://localhost:8501`

## Usage Guide 📖

### Step 1: Upload Files
- Click on the file uploader and select one or more GSTR-3B PDF files
- You can select files from multiple months in any order

### Step 2: Wait for Processing
- The app will automatically extract data from each PDF
- A progress bar shows the processing status
- Successfully processed files are marked with ✅
- Any failed files are clearly indicated with ❌

### Step 3: Review Data
- A data preview table shows the extracted information
- Verify that all data looks correct

### Step 4: Generate Report
- Click the "Create Consolidated Excel Report" button
- The app generates a professionally formatted Excel file

### Step 5: Download
- Click "Download Consolidated Excel" to save the file to your computer
- The Excel file contains all your consolidated GSTR-3B data

## File Structure 📁

```
gstr3b-consolidator/
├── app.py                 # Main Streamlit application
├── requirements.txt       # Python dependencies
├── README.md             # This file
├── .gitignore           # Git ignore configuration
├── LICENSE              # MIT License
└── docs/
    ├── SETUP_GUIDE.md   # Detailed setup instructions
    └── TROUBLESHOOTING.md # Common issues & solutions
```

## Output Format 📊

The generated Excel file includes:

### Main Sheet: GSTR-3B Consolidated
| Column | Description |
|--------|-------------|
| Period | Month/Year of the return |
| Outward Taxable (Other) | Taxable supplies (other than zero-rated/nil) |
| Outward Taxable (Zero Rated) | Zero-rated taxable supplies |
| Other Outward (Nil/Exempt) | Nil-rated and exempt supplies |
| Inward (Reverse Charge) | Inward supplies liable to reverse charge |
| IGST | Integrated GST amount |
| CGST | Central GST amount |
| SGST | State/UT GST amount |

**Plus an automatic TOTAL row** with SUM formulas for all columns.

## Technical Stack 🛠️

- **Frontend Framework**: Streamlit 1.28.1
- **Data Processing**: Pandas 2.0.3
- **PDF Extraction**: PyPDF2 3.0.1
- **Excel Generation**: OpenPyXL 3.1.2
- **Language**: Python 3.8+

## Common Issues & Troubleshooting 🔧

### Issue: "ModuleNotFoundError: No module named 'streamlit'"
**Solution**: Make sure you've activated the virtual environment and installed requirements:
```bash
pip install -r requirements.txt
```

### Issue: PDF data not extracting correctly
**Solution**: 
- Ensure the PDF is a valid, non-encrypted GSTR-3B form
- Try re-exporting the PDF from the GST portal
- Check that the PDF is not a scanned image (text-based PDFs work best)

### Issue: Port 8501 already in use
**Solution**: Run on a different port:
```bash
streamlit run app.py --server.port 8502
```

### Issue: Application runs slowly
**Solution**:
- Close other applications to free up RAM
- Process fewer files at once (max 12 files recommended)
- Restart the application

## Deployment 🌐

### Local Hosting (For Small Teams)
```bash
streamlit run app.py --server.headless true --server.port 8501
```

### Deploy to Streamlit Cloud
1. Push your repository to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Click "New app"
4. Select your repository, branch, and app file
5. Deploy!

### Deploy to Heroku
See `docs/DEPLOYMENT.md` for detailed Heroku deployment instructions.

## Security & Privacy 🔐

- ✅ **Local Processing**: All files are processed on your machine - no uploads to external servers
- ✅ **No Data Storage**: Files are processed in memory and deleted immediately after
- ✅ **No Tracking**: No analytics or tracking of user data
- ✅ **Open Source**: Code is transparent and available for review

## Contributing 🤝

We welcome contributions! Here's how:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## Development Guide

### Adding New Features
1. Create a new branch for your feature
2. Write clean, documented code
3. Test thoroughly before submitting a PR
4. Update README if adding significant features

### Bug Reports
- Use GitHub Issues to report bugs
- Include PDF sample if possible
- Describe steps to reproduce

## Roadmap 🗺️

Planned features:
- [ ] Support for GSTR-1, GSTR-2B returns
- [ ] Advanced filtering and sorting
- [ ] Multi-month trend analysis
- [ ] Custom report templates
- [ ] API endpoint for automation
- [ ] Dark mode theme
- [ ] Mobile app version

## License 📜

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support & Contact 📧

- **GitHub Issues**: For bug reports and feature requests
- **Email**: support@example.com
- **Documentation**: See `/docs` folder for detailed guides

## Changelog 📝

### Version 1.0.0 (Initial Release)
- Initial release with core functionality
- PDF extraction from GSTR-3B forms
- Excel consolidation and generation
- Professional UI with Streamlit
- Complete documentation

## FAQ ❓

### Q: Can I process 100+ files at once?
A: Yes, but it may take time depending on your system. Process in batches of 20-30 files for optimal performance.

### Q: What if a PDF fails to extract?
A: The app will show which files failed. Try re-downloading the PDF from the GST portal and re-uploading.

### Q: Can I use this for GSTR-1 or GSTR-2B?
A: Currently only GSTR-3B is supported. We're working on adding support for other forms.

### Q: Is there an API available?
A: Not yet, but it's on our roadmap for v2.0.

### Q: Can I run this offline?
A: Yes! Clone the repo and run locally. No internet required after installation.

## Credits 👏

- Built with [Streamlit](https://streamlit.io)
- PDF processing with [PyPDF2](https://pypdf2.readthedocs.io)
- Data handling with [Pandas](https://pandas.pydata.org)
- Excel generation with [OpenPyXL](https://openpyxl.readthedocs.io)

---

**Made with ❤️ for simplified GST compliance**

Happy consolidating! 🎉
