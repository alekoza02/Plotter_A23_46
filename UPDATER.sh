echo "Initializing submodules if needed..."
git submodule init
git submodule update --recursive --remote

echo "Pulling latest changes from main repository..."
git pull --recurse-submodules

echo "Updating all submodules to the correct commits..."
git submodule update --recursive

echo "All repositories and submodules are now up to date!"