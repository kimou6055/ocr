# OCR Django Project

This repository contains a minimal Django application that demonstrates how to
integrate PaddleOCR's **PP‑StructureV3** pipeline into a web interface. Users
can upload scanned document images via a browser and receive raw JSON-like
extraction results for any tables detected in the document.

The project is designed as a starting point: it handles file uploads,
invokes the OCR pipeline if available and displays results. You can extend
it to save results to a database, convert tables into CSV/Excel files or
render them as HTML tables.

## Prerequisites

* **Python 3.10+**
* **Django 4.2** or later
* **PaddleOCR 3.x** (optional during development)
* A supported PaddlePaddle backend (e.g. CUDA-enabled GPU or CPU)

To install the Python dependencies, run:

```bash
pip install -r requirements.txt
```

If you encounter issues installing PaddleOCR offline, refer to their
installation instructions on [GitHub](https://github.com/PaddlePaddle/PaddleOCR).

## Running the Project

1. Ensure that Django is installed and available on your PATH.
2. Navigate to the project directory:

   ```bash
   cd ocr_django_project
   ```

3. Apply database migrations (even though no models are defined yet):

   ```bash
   python manage.py migrate
   ```

4. Start the development server:

   ```bash
   python manage.py runserver
   ```

5. Open your browser and visit `http://127.0.0.1:8000/`. Use the form to
   upload a scanned document image. If PaddleOCR is installed, the
   application will attempt to extract tables and display the results.

## Notes

* The application uses Django's `FileSystemStorage` to save uploaded files in
  the `media/` directory. Make sure this directory is writable by your
  webserver.
* The raw results returned by PP‑StructureV3 are displayed as JSON-like
  strings. You can modify `views.py` to parse the results and present
  them in a more user-friendly format.
* When running in production, set `DEBUG = False` in `ocr_project/settings.py`,
  configure a secure `SECRET_KEY` and specify appropriate `ALLOWED_HOSTS`.

## License

This project is licensed under the Apache License 2.0, the same license
used by PaddleOCR.