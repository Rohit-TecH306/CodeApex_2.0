import bankData from '../data/bankData.json';

export default function Header() {
  const { name, tagline, branchName, branchCode, ifscCode } = bankData.profile;


  return (
    <header className="relative z-10 w-full py-8 px-12 flex justify-between items-center">
      <div className="flex flex-col">
        <div className="flex items-center gap-3 mb-1">
          <div className="w-10 h-10 bg-blue-600 rounded-xl flex items-center justify-center text-white font-bold text-xl shadow-md">
            �ų
          </div>
          <h1 className="text-2xl font-extrabold text-gray-900 tracking-tight">{name}</h1>
        </div>
        <p className="text-gray-500 font-medium tracking-wide ml-13">{tagline}</p>
      </div>

      <div className="flex flex-col items-end text-sm text-gray-600 font-medium">
        <p className="text-gray-900 font-bold text-base mb-1">{branchName}</p>
        <p>Branch Code: <span className="text-blue-600">{branchCode}</span></p>
        <p>IFSC: <span className="text-blue-600">{ifscCode}</span></p>
      </div>
    </header>
  );
}
