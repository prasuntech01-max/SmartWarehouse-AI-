const path = require('path');
const HtmlWebpackPlugin = require('html-webpack-plugin');
module.exports = {
  entry: {
    main: './src/index.js',
    lab_backdrop: './src/lab_backdrop.js',
  },
  output: {
    filename: (pathData) => (pathData.chunk.name === 'main' ? 'bundle.js' : '[name].js'),
    path: path.resolve(__dirname, 'dist'),
    clean: true,
  },
  module: {
    rules: [],
  },
  plugins: [
    new HtmlWebpackPlugin({
      template: './src/index.html',
      inject: false,
    }),
  ],
  performance: {
    hints: 'warning',
    maxAssetSize: 1024 * 1024,
    maxEntrypointSize: 1024 * 1024,
  },
  devServer: {
    static: {
      directory: path.join(__dirname, 'dist'),
    },
    compress: true,
    port: 3000,
  },
};
