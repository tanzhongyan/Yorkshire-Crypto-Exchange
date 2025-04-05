# Create .env in project root
cat <<EOF > .env
STRIPE_SECRET_KEY=sk_test_51R6j2MQarwElDC0RNMMB9gPLG1onYDEMChlfZOyjx66NRFCkASiY4688y1FNplTFYM6waI4vvqg6E1GoQNIMwbJB00xc2sAqrB
EOF

echo "✅ Created .env in project root"

# Make sure the deposit folder exists
mkdir -p ./api/composite/deposit

# Create .env inside ./api/composite/deposit
cat <<EOF > ./api/composite/deposit/.env
STRIPE_PUBLIC_KEY=pk_test_51R6j2MQarwElDC0RGmPcYnWcvXM6Cmh7MdB01NmCFKhkx8AgB14nRRwgawoGUSyNvA07etNR9LtS0ezWCXqWE0Ym00gpcFwWjb
STRIPE_SECRET_KEY=sk_test_51R6j2MQarwElDC0RNMMB9gPLG1onYDEMChlfZOyjx66NRFCkASiY4688y1FNplTFYM6waI4vvqg6E1GoQNIMwbJB00xc2sAqrB
STRIPE_WEBHOOK_SECRET=whsec_4a36df522b425cf190e7d6f4eac836fae600f9cd0f4b50c416765d8bcb23a4b1
EOF

echo "✅ Created .env in ./api/composite/deposit"