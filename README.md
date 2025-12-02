# Crop Manager Pro

Crop Manager Pro is a comprehensive desktop application designed for agricultural management and crop disease diagnosis. It utilizes deep learning to analyze plant images and detect diseases, generating detailed insights regarding symptoms, treatments, and prevention. Additionally, it features a robust inventory management system for tracking seeds, plants, fertilizers, and tools.

## Features

  * **AI Disease Diagnosis:** Uses a pre-trained Convolutional Neural Network (CNN) to detect crop diseases from images with high confidence.
  * **Automated Reporting:** Generates instant medical reports including causal pathogens, symptoms, and recommended treatments based on the diagnosis.
  * **Inventory Management:** A dedicated system to track farm stock (Plants, Seeds, Fertilizers, Tools) with add/delete functionality.
  * **Secure Authentication:** Local user authentication system with SHA-256 password hashing.
  * **Scan History:** Automatically logs all analysis results with timestamps for future reference.
  * **Modern UI:** A responsive, dark-themed interface built with CustomTkinter.
  * **Offline Capability:** Operates entirely locally using a JSON-based database and a local TensorFlow model.

## Technology Stack

  * **Language:** Python 3.13+
  * **GUI Framework:** CustomTkinter
  * **Machine Learning:** TensorFlow, Keras, TensorFlow Hub
  * **Image Processing:** Pillow (PIL), NumPy
  * **Data Storage:** JSON (Local flat-file database)

## Prerequisites

Ensure you have Python installed on your system. You will need the following dependencies:

  * customtkinter
  * tensorflow
  * tensorflow-hub
  * pillow
  * numpy

## Installation

1.  **Clone the Repository**

    ```bash
    git clone https://github.com/Anupssz/crop-manager-pro.git
    cd crop-manager-pro
    ```

2.  **Install Dependencies**

    ```bash
    pip install customtkinter tensorflow tensorflow-hub pillow numpy
    ```

3.  **Model Configuration**
    Ensure your project directory contains the AI model. The application supports two formats:

      * **Folder format (Recommended):** A folder named `my_model` containing `saved_model.pb` and the `variables` directory.
      * **File format:** A single file named `model.h5`.


## Usage

1.  **Run the Application**
    Execute the main script from your terminal:

    ```bash
    python main.py
    ```

2.  **Login**
    On the first run, the system initializes a default administrator account.

      * **Username:** admin
      * **Password:** admin

    *You can register new users via the "Create Account" button on the login screen.*

3.  **Dashboard Navigation**

      * **Disease Scan:** Upload an image of a leaf. Click "Generate Report" to receive an AI diagnosis.
      * **Inventory:** Use the "+ Add Item" button to manage your farm stock.
      * **History:** View logs of previous scans and their results.

## Project Structure

```text
crop-manager-pro/
├── main.py              # Application entry point and logic
├── classes.txt          # List of plant disease class labels
├── user_data.json       # Encrypted user database (Auto-generated)
├── my_model/            # TensorFlow SavedModel folder
│   ├── saved_model.pb
│   └── variables/
└── README.md            # Project documentation
```

## Troubleshooting

**Issue: "AI Fail: name 'np' is not defined"**
Ensure NumPy is imported at the top of your script. The current release includes this fix.

**Issue: Model Load Failure**
If you receive a Keras 3 compatibility error, the application will automatically attempt to switch to `TFSMLayer` mode. Ensure your `my_model` folder structure is correct and not nested inside another folder.

**Issue: UI Freezing on Startup**
The application uses threading to load TensorFlow libraries. If the loading screen persists for more than 1 minute, check your console for Python errors regarding missing libraries.

## License

This project is open-source and available under the MIT License.

## Acknowledgements

  * Dataset: PlantVillage
  * Model Architecture: MobileNetV2 / ResNet50
  * UI Design: CustomTkinter Library
