import argostranslate.package
import argostranslate.translate

# List of source language codes
source_languages = [
    "ar", "az", "ca", "zh", "cs", "da", "nl", "eo", "fi", "fr", 
    "de", "el", "he", "hi", "hu", "id", "ga", "it", "ja", "ko", 
    "fa", "pl", "pt", "ru", "sk", "es", "sv", "tr", "uk"
]

to_code = "en"

# Update package index
argostranslate.package.update_package_index()
available_packages = argostranslate.package.get_available_packages()
try:
    for from_code in source_languages:
        try:
            print(f"installing {from_code}")
            package_to_install = next(
                filter(
                    lambda x: x.from_code == from_code and x.to_code == to_code, available_packages
                )
            )
            argostranslate.package.install_from_path(package_to_install.download())
            print(f"finished installing {from_code}")
        except Exception as e:
            print(f"Failed to install language: {from_code}")
    

    print("The installation finished successfully")
except Exception as e:
    print(f"An error ocurred during the installation")
    print(e)
