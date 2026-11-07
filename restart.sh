#!/bin/bash
set -e
echo "Restarting picture.service..."
sudo systemctl restart picture.service
echo "Done!"